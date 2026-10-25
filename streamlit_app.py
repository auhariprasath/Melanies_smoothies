
# Import Python packages
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import col

# App title and description
st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

# Customer name input
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be:", name_on_order)

# Connect to Snowflake
session = get_active_session()

# Fetch available fruits
my_dataframe = session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
fruit_rows = my_dataframe.select(col("FRUIT_NAME")).collect()
fruit_options = [row["FRUIT_NAME"] for row in fruit_rows]

# Choose up to 5 ingredients
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5
)

# Submit smoothie order
if st.button("Submit Order"):
    if not name_on_order.strip():
        st.warning("Please enter your name.")
    elif not ingredients_list:
        st.warning("Please choose at least one fruit.")
    else:
        ingredients_string = " ".join(ingredients_list)

        my_insert_stmt = """
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                (NAME_ON_ORDER, INGREDIENTS)
            VALUES (?, ?)
        """

        session.sql(
            my_insert_stmt,
            params=[name_on_order.strip(), ingredients_string]
        ).collect()

        st.success(
            f"Your Smoothie is ordered, {name_on_order.strip()}!",
            icon="✅"
        )
