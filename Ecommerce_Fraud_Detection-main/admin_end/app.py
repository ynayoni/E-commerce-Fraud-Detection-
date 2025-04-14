from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import pickle

app = Flask(__name__, template_folder='template')

# Connect to MongoDB
client = MongoClient('localhost', 27017)
db = client.fraud_detection
#test
fraud_data_collection = db.user_profile
fraud_log_col = db.fraud_log
user_details_col = db.User_Details  
with open('Fraud_rf.pickle', 'rb') as file:
    model = pickle.load(file)

def notify_new_user(user_data):
    print("New user added:", user_data)


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/fraud_detection')
def fraud_detection():
    return render_template('fraud_detection.html')

@app.route('/custom_check')
def custom_check():
    return render_template('custom_check.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        # Get data from form for fraud detection
        purchase_value = float(request.form['purchase_value'])
        age = int(request.form['age'])
        country = request.form['country']
        time_spent = float(request.form['time_spent'])

        # Dummy prediction logic for demonstration
        prediction = 'Fraudulent' if purchase_value > 100 else 'Not Fraudulent'
        fraud_probability = 0.75 if prediction == 'Fraudulent' else 0.25

        return jsonify({'prediction': prediction, 'fraud_probability': fraud_probability})

@app.route('/user/<int:user_id>')
def get_user_data(user_id):
    user_data_cursor = fraud_log_col.find({'user_id': user_id}, {'_id': False})
    user_data_list = list(user_data_cursor)

    if user_data_list:
        features = []
        for data in user_data_list:
            feature_values = [data[feature] if feature in data else 0 for feature in sorted(data.keys())[:195] if isinstance(data.get(feature), (int, float))]
            while len(feature_values) < 195:  # Pad with 0s if there are fewer than 195 features
                feature_values.append(0)
            features.append(feature_values)
        predictions = model.predict(features)
        fraud_probabilities = model.predict_proba(features)[:, 1]
        print(predictions)
        print(fraud_probabilities)
        fraud_prediction = ['Fraudulent' if pred == 1 else 'Not Fraudulent' for pred in predictions]
        for data, prediction, prob in zip(user_data_list, fraud_prediction, fraud_probabilities):
            data['fraud_prediction'] = prediction
            data['fraud_probability'] = prob.item()

        return jsonify({'user_id': user_id, 'data': user_data_list})
    else:
        return jsonify({'error': 'User not found'})

@app.route('/ban/<int:user_id>', methods=['POST'])
def ban_account(user_id):
    # Update fraud_log collection
    result = fraud_log_col.update_many({'user_id': user_id}, {'$set': {'class': 1}})

    # Update User_Details collection if the document exists
    if result.modified_count > 0:
        user_details_col.update_many({'_id': user_id}, {'$set': {'class': 1}})
        return jsonify({'success': 'Account banned successfully!'})
    else:
        return jsonify({'error': 'Account not found'})

@app.route('/new_user_data', methods=['GET', 'POST'])  # Allow both GET and POST methods
def new_user_data():
    if request.method == 'GET':
        # Query User_Details collection for new user data
        user_data_cursor = user_details_col.find({}, {'_id': True, 'email': True, 'country': True, 'purchase_value': True, 'class': True})

        user_data_list = list(user_data_cursor)

        # Notify about new user data
        for user_data in user_data_list:
            notify_new_user(user_data)
            # Add user_id field to each document
            user_data['user_id'] = user_data.pop('_id')

        print("User data list:", user_data_list)  
        return jsonify(user_data_list)  # Return user data from User_Details collection as JSON
    elif request.method == 'POST':

        pass

@app.route('/class_data')
def class_data():
    class_data_cursor = fraud_log_col.find({}, {'_id': False, 'class': True})
    class_data_list = list(class_data_cursor)
    return jsonify(class_data_list)

@app.route('/age_distribution')
def age_distribution():
    # Fetch age distribution data for fraudulent class (class 1)
    age_data_cursor = fraud_log_col.aggregate([
        {'$match': {'class': 1}},
        {'$group': {'_id': '$age', 'count': {'$sum': 1}}}
    ])

    age_distribution_data = [{'age': entry['_id'], 'count': entry['count']} for entry in age_data_cursor]

    return jsonify(age_distribution_data)

@app.route('/purchase_value_distribution')
def purchase_value_distribution():
    # Fetch purchase value distribution data for fraudulent class (class 1)
    purchase_value_data_cursor = fraud_log_col.aggregate([
        {'$match': {'class': 1}},
        {'$group': {'_id': '$purchase_value', 'count': {'$sum': 1}}}
    ])

    purchase_value_distribution_data = [{'purchase_value': entry['_id'], 'count': entry['count']} for entry in purchase_value_data_cursor]

    return jsonify(purchase_value_distribution_data)

if __name__ == '__main__':
    app.run(debug=True, port=3000)
