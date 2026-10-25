
import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col

# App title and description
st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom smoothie!")

# Customer name input
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your smoothie will be:", name_on_order)


# Connect to Snowflake using Streamlit Secrets
@st.cache_resource
def create_session():
    connection_parameters = dict(
        st.secrets["connections"]["snowflake"]
    )

    # Keep the database and schema consistent
    connection_parameters["database"] = "SMOOTHIES"
    connection_parameters["schema"] = "PUBLIC"

    return Session.builder.configs(connection_parameters).create()


try:
    session = create_session()

    # Fetch available fruits
    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col("FRUIT_NAME"))
        .collect()
    )

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

            insert_stmt = """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (NAME_ON_ORDER, INGREDIENTS)
                VALUES (?, ?)
            """

            session.sql(
                insert_stmt,
                params=[
                    name_on_order.strip(),
                    ingredients_string
                ]
            ).collect()

            st.success(
                f"Your smoothie is ordered, {name_on_order.strip()}!",
                icon="✅"
            )

except Exception as e:
    st.error("Unable to connect to Snowflake or load the fruits.")
    st.exception(e)
