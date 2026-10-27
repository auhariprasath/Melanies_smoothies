import base64

import pandas as pd
import requests
import streamlit as st

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from snowflake.snowpark.functions import col


# App title
st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")


# Connect to Snowflake using the Base64 private key
try:
    key_b64 = st.secrets["snowflake_auth"]["private_key_b64"]

    pem_bytes = base64.b64decode(key_b64)

    private_key_obj = serialization.load_pem_private_key(
        pem_bytes,
        password=None,
    )

    private_key_der = private_key_obj.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )

    cnx = st.connection(
        "snowflake",
        private_key=private_key_der,
    )

    session = cnx.session()

    # Test the connection before continuing
    session.sql("SELECT CURRENT_USER()").collect()

except Exception as error:
    st.error(
        f"Snowflake connection failed: "
        f"{type(error).__name__}: {error}"
    )
    st.stop()


# Load fruit names and search terms
my_dataframe = session.table(
    "SMOOTHIES.PUBLIC.FRUIT_OPTIONS"
).select(
    col("FRUIT_NAME"),
    col("SEARCH_ON"),
)

pd_df = my_dataframe.to_pandas()

# Display fruit options
st.dataframe(pd_df, use_container_width=True)


# Customer name
name_on_order = st.text_input("Name on Smoothie:")

if name_on_order.strip():
    st.write(
        f"The name on your Smoothie will be: "
        f"{name_on_order.strip()}"
    )


# Choose up to 5 ingredients
fruit_list = pd_df["FRUIT_NAME"].tolist()

ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_list,
    max_selections=5,
)


# Build ingredients string and retrieve nutrition data
ingredients_string = ""

if ingredients_list:
    for fruit_chosen in ingredients_list:
        # Preserve the original ingredient-building logic
        ingredients_string += fruit_chosen

        search_on = pd_df.loc[
            pd_df["FRUIT_NAME"] == fruit_chosen,
            "SEARCH_ON",
        ].iloc[0]

        st.write(
            "The search value for",
            fruit_chosen,
            "is",
            search_on,
            ".",
        )

        st.subheader(
            fruit_chosen + " Nutrition Information"
        )

        try:
            response = requests.get(
                "https://my.smoothiefroot.com/api/fruit/"
                + requests.utils.quote(
                    str(search_on), safe=""
                ),
                timeout=10,
            )

            if response.status_code == 200:
                sf_df = pd.json_normalize(response.json())
                st.dataframe(
                    sf_df,
                    use_container_width=True,
                )

            elif response.status_code == 404:
                st.info(
                    "Sorry, that fruit is not in our database."
                )

            else:
                st.warning(
                    f"API returned HTTP {response.status_code}."
                )

        except requests.RequestException as error:
            st.warning(
                f"Could not retrieve fruit data: {error}"
            )

    st.write(
        "Your ingredients:",
        ", ".join(ingredients_list),
    )


# Submit order
if st.button("Submit Order"):
    if not name_on_order.strip():
        st.warning("Please enter your name.")

    elif not ingredients_list:
        st.warning("Please select at least one ingredient.")

    else:
        try:
            session.sql(
                """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (INGREDIENTS, NAME_ON_ORDER)
                VALUES (?, ?)
                """,
                params=[
                    ingredients_string.strip(),
                    name_on_order.strip(),
                ],
            ).collect()

            st.success(
                f"Your smoothie is ordered, "
                f"{name_on_order.strip()}!",
                icon="✅",
            )

        except Exception as error:
            st.error(
                f"Could not save your order: {error}"
            )
