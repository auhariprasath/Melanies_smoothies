
import base64
import requests
import pandas as pd
import streamlit as st

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col
from cryptography.hazmat.primitives import serialization


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered",
)

st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")


# --------------------------------------------------
# SMOOTHIE ORDER INPUTS
# --------------------------------------------------
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your smoothie will be:", name_on_order)


# --------------------------------------------------
# SNOWFLAKE CONNECTION
# --------------------------------------------------
@st.cache_resource
def create_session():
    cfg = st.secrets["connections"]["snowflake"]

    private_key_bytes = base64.b64decode(cfg["private_key_b64"])

    private_key = serialization.load_pem_private_key(
        private_key_bytes,
        password=None,
    )

    private_key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    connection_parameters = {
        "account": cfg["account"],
        "user": cfg["user"],
        "private_key": private_key_der,
        "role": cfg["role"],
        "warehouse": cfg["warehouse"],
        "database": cfg["database"],
        "schema": cfg["schema"],
    }

    return Session.builder.configs(connection_parameters).create()


# --------------------------------------------------
# LOAD FRUITS AND SUBMIT ORDERS
# --------------------------------------------------
try:
    session = create_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col("FRUIT_NAME"))
        .collect()
    )

    fruit_options = [row["FRUIT_NAME"] for row in fruit_rows]

    if not fruit_options:
        st.warning("No fruits found. Check the FRUIT_OPTIONS table.")

    else:
        ingredients_list = st.multiselect(
            "Choose up to 5 ingredients:",
            options=fruit_options,
            max_selections=5,
        )

        if st.button("Submit Order", type="primary"):
            if not name_on_order.strip():
                st.warning("Please enter your name.")

            elif not ingredients_list:
                st.warning("Please choose at least one fruit.")

            else:
                ingredients_string = " ".join(ingredients_list)

                insert_stmt = """
                    INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (NAME_ON_ORDER, INGREDIENTS)
                    VALUES (?, ?)
                """

                session.sql(
                    insert_stmt,
                    params=[
                        name_on_order.strip(),
                        ingredients_string,
                    ],
                ).collect()

                st.success(
                    f"Your smoothie is ordered, {name_on_order.strip()}!",
                    icon="✅",
                )

except Exception as e:
    st.error("Unable to connect to Snowflake or load fruits.")
    st.caption(f"Error details: {str(e)}")


# --------------------------------------------------
# SMOOTHIEFROOT API - WATERMELON NUTRITION
# --------------------------------------------------
st.divider()
st.subheader("🍉 SmoothieFroot Nutrition Information")

try:
    response = requests.get(
        "https://my.smoothiefroot.com/api/fruit/watermelon",
        timeout=15,
    )
    response.raise_for_status()

    fruit_data = response.json()

    # Extract the nested nutrition dictionary
    nutrition_values = fruit_data.get("nutrition", {})

    # Create one row for each nutrient
    rows = []

    for nutrient, value in nutrition_values.items():
        rows.append({
            "nutrition": nutrient,
            "family": fruit_data.get("family"),
            "genus": fruit_data.get("genus"),
            "id": fruit_data.get("id"),
            "name": fruit_data.get("name"),
            "nutrition_value": value,
            "order": fruit_data.get("order"),
        })

    smoothiefruit_df = pd.DataFrame(rows)

    # Match the workshop's table layout:
    # nutrient name, family, genus, id, name, value, order
    if not smoothiefruit_df.empty:
        smoothiefruit_df = smoothiefruit_df[
            [
                "nutrition",
                "family",
                "genus",
                "id",
                "name",
                "nutrition_value",
                "order",
            ]
        ]

        # Rename columns to match the workshop screenshot
        smoothiefruit_df = smoothiefruit_df.rename(
            columns={
                "nutrition": "nutrient",
                "nutrition_value": "nutrition",
            }
        )

        st.dataframe(
            smoothiefruit_df,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.warning("No nutrition data was returned by the API.")

except requests.RequestException as e:
    st.warning("Unable to retrieve SmoothieFroot API data.")
    st.caption(f"API error: {str(e)}")

except (ValueError, TypeError, KeyError) as e:
    st.warning("Unable to format the SmoothieFroot API response.")
    st.caption(f"Response error: {str(e)}")
