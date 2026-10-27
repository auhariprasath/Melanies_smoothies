
import streamlit as st
import pandas as pd
import requests
import base64

from cryptography.hazmat.primitives import serialization
from snowflake.snowpark import Session


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered"
)

st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")


# --------------------------------------------------
# SNOWFLAKE CONNECTION - KEY PAIR AUTHENTICATION
# --------------------------------------------------

@st.cache_resource
def create_session():
    cfg = st.secrets["connections"]["snowflake"]

    private_key_b64 = cfg["private_key_b64"].strip()
    private_key_bytes = base64.b64decode(private_key_b64)

    private_key = serialization.load_pem_private_key(
        private_key_bytes,
        password=None
    )

    private_key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    connection_parameters = {
        "account": cfg["account"],
        "user": cfg["user"],
        "private_key": private_key_der,
        "authenticator": "SNOWFLAKE_JWT",
        "role": cfg.get("role", "SYSADMIN"),
        "warehouse": cfg.get("warehouse", "COMPUTE_WH"),
        "database": cfg.get("database", "SMOOTHIES"),
        "schema": cfg.get("schema", "PUBLIC")
    }

    return Session.builder.configs(
        connection_parameters
    ).create()


# --------------------------------------------------
# CONNECT AND LOAD FRUIT OPTIONS
# --------------------------------------------------

try:
    session = create_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select("FRUIT_NAME", "SEARCH_ON")
        .collect()
    )

    fruit_options = {}

    for row in fruit_rows:
        fruit_name = row["FRUIT_NAME"]
        search_on = row["SEARCH_ON"]

        fruit_options[fruit_name] = (
            search_on if search_on else fruit_name
        )

except Exception as e:
    st.error("Unable to load fruit options from Snowflake.")
    st.code(str(e))
    st.stop()


# --------------------------------------------------
# SMOOTHIE ORDER FORM
# --------------------------------------------------

name_on_order = st.text_input("Name on Smoothie:")

st.write(
    "The name on your smoothie will be:",
    name_on_order
)

ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=list(fruit_options.keys()),
    max_selections=5
)


# --------------------------------------------------
# GET NUTRITION DATA FROM SMOOTHIEFROOT API
# --------------------------------------------------

def get_fruit_nutrition(search_name):
    url = (
        "https://my.smoothiefroot.com/api/fruit/"
        + requests.utils.quote(search_name, safe="")
    )

    try:
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return None, "This fruit was not found in the API."

        data = response.json()

        if isinstance(data, list):
            if not data:
                return None, "No nutrition data available."
            data = data[0]

        if not isinstance(data, dict):
            return None, "Unexpected API response."

        nutrition = data.get("nutrition", {})

        if not isinstance(nutrition, dict) or not nutrition:
            return None, "No nutrition information available."

        rows = []

        for nutrient, amount in nutrition.items():
            rows.append({
                "": nutrient,
                "family": data.get("family", ""),
                "genus": data.get("genus", ""),
                "id": data.get("id", ""),
                "name": data.get("name", search_name),
                "nutrition": amount,
                "order": data.get("order", "")
            })

        return pd.DataFrame(rows), None

    except requests.RequestException as e:
        return None, f"API request failed: {e}"
    except (ValueError, TypeError) as e:
        return None, f"Unable to parse API response: {e}"


# --------------------------------------------------
# DISPLAY NUTRITION TABLES
# --------------------------------------------------

if ingredients_list:
    st.divider()
    st.subheader("🍉 SmoothieFroot Nutrition Information")

    for fruit_chosen in ingredients_list:
        search_name = fruit_options[fruit_chosen]

        st.subheader(
            f"{fruit_chosen} Nutrition Information"
        )

        nutrition_df, error_message = get_fruit_nutrition(
            search_name
        )

        if nutrition_df is not None:
            st.dataframe(
                nutrition_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning(
                f"{fruit_chosen}: {error_message}"
            )


# --------------------------------------------------
# SUBMIT ORDER TO SNOWFLAKE
# --------------------------------------------------

if st.button("Submit Order", type="primary"):
    if not name_on_order.strip():
        st.warning("Please enter your name.")

    elif not ingredients_list:
        st.warning("Please choose at least one fruit.")

    else:
        try:
            ingredients_string = " ".join(ingredients_list)

            session.sql(
                """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (NAME_ON_ORDER, INGREDIENTS)
                VALUES (?, ?)
                """,
                params=[
                    name_on_order.strip(),
                    ingredients_string
                ]
            ).collect()

            st.success(
                f"Your smoothie is ordered, "
                f"{name_on_order.strip()}! 🥤"
            )

        except Exception as e:
            st.error("Unable to save your smoothie order.")
            st.code(str(e))
