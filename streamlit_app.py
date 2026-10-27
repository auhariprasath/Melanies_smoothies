
import streamlit as st
import pandas as pd
import requests

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="wide"
)

st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

# --------------------------------------------------
# SNOWFLAKE CONNECTION
# --------------------------------------------------

@st.cache_resource
def create_session():
    connection_parameters = dict(
        st.secrets["connections"]["snowflake"]
    )

    return Session.builder.configs(
        connection_parameters
    ).create()


# --------------------------------------------------
# LOAD FRUIT OPTIONS FROM SNOWFLAKE
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

        # If SEARCH_ON is empty, use the displayed fruit name.
        if not search_on:
            search_on = fruit_name

        fruit_options[fruit_name] = search_on

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
# SMOOTHIEFRUIT API FUNCTION
# --------------------------------------------------

def get_fruit_nutrition(search_name):
    url = (
        "https://my.smoothiefroot.com/api/fruit/"
        + requests.utils.quote(search_name, safe="")
    )

    try:
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return None, (
                f"Fruit '{search_name}' was not found "
                "in the SmoothieFroot database."
            )

        data = response.json()

        if isinstance(data, list):
            if not data:
                return None, "No nutrition data was returned."
            data = data[0]

        if not isinstance(data, dict):
            return None, "Unexpected API response format."

        # Nutrition is usually a nested dictionary.
        nutrition = data.get("nutrition", {})

        if not isinstance(nutrition, dict):
            return None, "Nutrition information is unavailable."

        if not nutrition:
            return None, "No nutrition information is available."

        # Create the workshop-style table:
        # carbs, fat, protein, sugar as separate rows.
        table_rows = []

        for nutrient, amount in nutrition.items():
            table_rows.append({
                "": nutrient,
                "family": data.get("family", ""),
                "genus": data.get("genus", ""),
                "id": data.get("id", ""),
                "name": data.get("name", search_name),
                "nutrition": amount,
                "order": data.get("order", "")
            })

        return pd.DataFrame(table_rows), None

    except requests.RequestException as e:
        return None, f"API connection failed: {e}"
    except (ValueError, TypeError) as e:
        return None, f"Unable to read API response: {e}"


# --------------------------------------------------
# DISPLAY NUTRITION INFORMATION FOR EACH FRUIT
# --------------------------------------------------

if ingredients_list:
    st.divider()
    st.subheader("🍉 SmoothieFroot Nutrition Information")

    for fruit_chosen in ingredients_list:
        search_name = fruit_options[fruit_chosen]

        st.subheader(f"{fruit_chosen} Nutrition Information")

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
# SUBMIT ORDER
# --------------------------------------------------

if st.button("Submit Order", type="primary"):
    if not name_on_order.strip():
        st.warning("Please enter your name.")

    elif not ingredients_list:
        st.warning("Please choose at least one fruit.")

    else:
        try:
            ingredients_string = " ".join(ingredients_list)

            insert_statement = """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (NAME_ON_ORDER, INGREDIENTS)
                VALUES (?, ?)
            """

            session.sql(
                insert_statement,
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
