from flask import Flask, render_template, request, redirect, session, jsonify
from pymongo import MongoClient, UpdateOne
from uuid import uuid4
from bson.objectid import ObjectId
from random import randint, choice
from datetime import datetime
import string

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'
client = MongoClient('mongodb://localhost:27017/')
db = client['fraud_detection']
user_details_collection = db['User_Details']
user_profile_collection = db['user_profile']  

user_id_counter = db['user_id_counter']

if user_id_counter.count_documents({}) == 0:
    user_id_counter.insert_one({'_id': 'user_id', 'value': 1})

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/home')
def home():
    return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            existing_user = user_details_collection.find_one({'email': email, 'password': password})
            print(existing_user)
            if existing_user:
                session['user_id'] = str(existing_user['_id'])
                print("User ID set in session:", session['user_id'])
                return redirect('/marketplace')  
            else:
                return render_template('login.html', message='Invalid email or password.')

        except Exception as e:
            return render_template('login.html', message='An error occurred while processing your request.')
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    if 'user_id' in session:
        banned_user = user_details_collection.find_one({'_id': int(session['user_id']), 'class': 1})
        if banned_user:
            session.clear()


    email = request.form['email']
    password = request.form['password']
    gender = request.form['gender']
    country = request.form['country']
    age = int(request.form['age']) 

    existing_user = user_details_collection.find_one({'email': email})
    if existing_user:
        return render_template('registration_error.html', message='Account already exists')
    user_id = user_id_counter.find_one_and_update(
        {'_id': 'user_id'},
        {'$inc': {'value': 1}},
        return_document=True
    )['value']

    
    user_data = {
        '_id': user_id,  # Set user_id as _id
        'user_id': user_id,  # Add user_id field
        'email': email,
        'password': password,
        'gender': gender,
        'country': country,
        'age': age,  # Include age in user data
        'class': 0,  # Set class as 0 for new users
        # Set gender as 'M' if male and 'F' if female
        'M': 1 if gender == 'M' else 0,
        'F': 1 if gender == 'F' else 0
    }
    user_details_collection.insert_one(user_data)

    session['user_id'] = user_id
    return redirect('/marketplace')

@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect('/login')

    print("Session user_id:", session['user_id'])

    try:
        user = user_details_collection.find_one({'_id': int(session['user_id'])})  
        print("User data:", user)

        if user is None:
            # Redirect to login page if user is not found
            return redirect('/login')

        # Check if the user is banned
        if user.get('class') == 1:
            return render_template('banned.html')  # Render the banned page

        cart_collection = db['cart']
        # Retrieve cart items from the cart collection
        cart_items = list(cart_collection.find({}, {'_id': 0}))

        return render_template('marketplace.html', email=user['email'], cart_items=cart_items)
    
    except Exception as e:
        # Handle any exceptions, such as database connection errors
        return render_template('login.html', message='An error occurred while processing your request.')




@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    product_id = int(data.get('productId'))

    # Map product ID to product name and price
    products = {
        1: {'name': 'Product 1', 'price': 10},
        2: {'name': 'Product 2', 'price': 20},
        3: {'name': 'Product 3', 'price': 30},
        4: {'name': 'Product 4', 'price': 40}
    }

    product = products.get(product_id)

    if product is None:
        return jsonify({'error': 'Invalid product ID'}), 400

    cart_collection = db['cart']

    # Check if the product already exists in the cart
    existing_product = cart_collection.find_one({'product_name': product['name']})

    if existing_product:
        # If the product exists, increment the quantity by 1 and update the total price
        cart_collection.update_one(
            {'product_name': product['name']},
            {'$inc': {'quantity': 1},
             '$set': {'total_price': (existing_product['quantity'] + 1) * product['price']}}
        )
    else:
        # If the product does not exist, insert a new entry with total price
        cart_collection.insert_one({'product_name': product['name'], 'quantity': 1, 'price': product['price'], 'total_price': product['price']})

    return jsonify({'message': 'Product added to cart'}), 200


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect('/login')


    cart_collection = db['cart']
    # Retrieve cart items from the cart collection
    cart_items = list(cart_collection.find({}, {'_id': 0}))

    # Calculate total price for each product
    total_sum = sum(item['total_price'] for item in cart_items)

    # Retrieve user data from the database using user_id
    user = user_details_collection.find_one({'_id': session['user_id']})

    return render_template('cart.html', email=user['email'], cart_items=cart_items, total_sum=total_sum)


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    product_name = data.get('productName')

  
    cart_collection = db['cart']

    # Remove the product from the cart collection
    cart_collection.delete_one({'product_name': product_name})

    return jsonify({'message': 'Product removed from cart'}), 200

@app.route('/increment_quantity', methods=['POST'])
def increment_quantity():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    product_name = data.get('productName')

   
    cart_collection = db['cart']

    # Check if the product exists in the cart
    existing_product = cart_collection.find_one({'product_name': product_name})

    if existing_product:
        # If the product exists, increment its quantity by 1
        cart_collection.update_one(
            {'product_name': product_name},
            {'$inc': {'quantity': 1}}
        )
        return jsonify({'message': 'Quantity incremented'}), 200
    else:
        return jsonify({'error': 'Product not found in cart'}), 404
@app.route('/decrement_quantity', methods=['POST'])
def decrement_quantity():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    product_name = data.get('productName')

    
    cart_collection = db['cart']

    # Check if the product exists in the cart
    existing_product = cart_collection.find_one({'product_name': product_name})

    if existing_product:
        # Decrement the quantity of the product by 1
        new_quantity = existing_product['quantity'] - 1

        if new_quantity <= 0:
            # If the new quantity is less than or equal to 0, remove the product from the cart
            cart_collection.delete_one({'product_name': product_name})
        else:
            # Otherwise, update the quantity in the cart
            cart_collection.update_one(
                {'product_name': product_name},
                {'$set': {'quantity': new_quantity}}
            )
        
        return jsonify({'message': 'Quantity decremented'}), 200
    else:
        return jsonify({'error': 'Product not found in cart'}), 404
from datetime import datetime
from random import choice, randint
import string

@app.route('/purchase', methods=['POST'])
def purchase():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Verify user credentials
    user = user_details_collection.find_one({'_id': session['user_id'], 'email': email, 'password': password})

    if user:
        # Calculate total sum of all product prices in the cart
        cart_collection = db['cart']
        cart_items = list(cart_collection.find({}, {'_id': 0}))
        total_sum = sum(item['total_price'] for item in cart_items)

        # Update purchase_value in User_Details collection
        user_details_collection.update_one(
            {'_id': session['user_id']},
            {'$inc': {'purchase_value': total_sum}}
        )

        # Clear the cart after purchase
        cart_collection.delete_many({})
        countries = [
                        'Afghanistan', 'Albania', 'Algeria', 'Angola', 'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria', 
                        'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bermuda', 
                        'Bhutan', 'Bolivia', 'Bonaire; Sint Eustatius; Saba', 'Bosnia and Herzegowina', 'Botswana', 'Brazil',
                        'British Indian Ocean Territory', 'Brunei Darussalam', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia',
                        'Cameroon', 'Canada', 'Cape Verde', 'Cayman Islands', 'Chile', 'China', 'Colombia', 'Congo', 
                        'Congo The Democratic Republic of The', 'Costa Rica', 'Cote D\'ivoire', 'Croatia (LOCAL Name: Hrvatska)', 
                        'Cuba', 'Curacao', 'Cyprus', 'Czech Republic', 'Denmark', 'Djibouti', 'Dominica', 
                        'Dominican Republic', 'Ecuador', 'Egypt', 'El Salvador', 'Estonia', 'Ethiopia', 'European Union',
                        'Faroe Islands', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Gibraltar', 
                        'Greece', 'Guadeloupe', 'Guam', 'Guatemala', 'Haiti', 'Honduras', 'Hong Kong', 'Hungary', 'Iceland', 'India', 
                        'Indonesia', 'Iran (ISLAMIC Republic Of)', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan',
                        'Kazakhstan', 'Kenya', 'Korea Republic of', 'Kuwait', 'Kyrgyzstan', 'Lao People\'s Democratic Republic', 'Latvia',
                        'Lebanon', 'Lesotho', 'Libyan Arab Jamahiriya', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'Macau', 'Macedonia', 
                        'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Malta', 'Mauritius', 'Mexico', 'Moldova Republic of', 'Monaco', 
                        'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nauru', 'Nepal', 'Netherlands', 
                        'New Caledonia', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'Norway', 'Oman', 'Pakistan',
                        'Palestinian Territory Occupied', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines',
                        'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Reunion', 'Romania', 'Russian Federation', 'Rwanda',
                        'Saint Kitts and Nevis', 'Saint Martin', 'San Marino', 'Saudi Arabia', 'Senegal', 'Serbia', 'Seychelles',
                        'Singapore', 'Slovakia (SLOVAK Republic)', 'Slovenia', 'South Africa', 'South Sudan', 'Spain', 'Sri Lanka',
                        'Sudan', 'Sweden', 'Switzerland', 'Syrian Arab Republic', 'Taiwan; Republic of China (ROC)', 'Tajikistan', 
                        'Tanzania United Republic of', 'Thailand', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan',
                        'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 'Uruguay', 'Uzbekistan',
                        'Vanuatu', 'Venezuela', 'Viet Nam', 'Virgin Islands (U', 'Yemen', 'Zambia', 'Zimbabwe'
                    ]

        # Generate fraud log data based on user details
        fraud_log_data = {
            'user_id': user['_id'],
            'purchase_value': total_sum,
            'age': user['age'],
            'class': user['class'],
            'time_spent': 0,  
            'Ads': 0,  
            'Direct': 0,
            'SEO': 1,  # Default value for SEO
            'Chrome': 1,  # Default value for Chrome browser
            'FireFox': 0,
            'IE': 0,
            'Opera': 0,
            'Safari': 0,
            'F': 0,
            'M': 0,
            **{country: 1 if user['country'] == country else 0 for country in countries} 
        }

        # Insert data into fraud_log collection
        fraud_log_collection = db['fraud_log']
        fraud_log_collection.insert_one(fraud_log_data)

        return jsonify({'message': 'Purchase successful'}), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/clear_session', methods=['POST'])
def clear_session():
    session.clear()
    return jsonify({'message': 'Session cleared'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=4000)
