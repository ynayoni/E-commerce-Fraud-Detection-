import numpy as np

def preprocess_input(raw_data):
    # Define categories for one-hot encoding
    source_types = ['SEO', 'Ads', 'Direct']
    browser_types = ['Chrome', 'Firefox', 'Safari', 'Opera', 'Edge', 'Other']
    sex_types = ['M', 'F']
    country_types = ['USA', 'UK', 'Canada', 'Germany', 'France', 'Japan', 'Other']

    # Initialize encoded features
    encoded_features = []

    # Preprocess categorical features
    for row in raw_data:
        encoded_row = []

        # One-hot encoding for 'source' feature
        source_encoded = [1 if row[2] == source_type else 0 for source_type in source_types]
        encoded_row.extend(source_encoded)

        # One-hot encoding for 'browser' feature
        browser_encoded = [1 if row[3] == browser_type else 0 for browser_type in browser_types]
        encoded_row.extend(browser_encoded)

        # One-hot encoding for 'sex' feature
        sex_encoded = [1 if row[4] == sex_type else 0 for sex_type in sex_types]
        encoded_row.extend(sex_encoded)

        # One-hot encoding for 'country' feature
        country_encoded = [1 if row[7] == country_type else 0 for country_type in country_types]
        encoded_row.extend(country_encoded)

        # Append numerical features
        encoded_row.extend([float(row[i]) for i in [0, 1, 5, 6]])

        encoded_features.append(encoded_row)

    return np.array(encoded_features)

# Example usage
if __name__ == "__main__":
    # Sample input data
    raw_data = [
        [0, 34, 'SEO', 'Chrome', 'M', 39, 0, 'Japan', 0.434673],
        [1, 16, 'Ads', 'Chrome', 'F', 53, 0, 'United States', 0.001731]
    ]

    # Preprocess input data
    preprocessed_data = preprocess_input(raw_data)
    print("Preprocessed data:")
    print(preprocessed_data)
