
import streamlit as st
import pandas as pd
import requests
from snowflake.snowpark.functions import col

# App title
st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

# Connect to Snowflake using Streamlit connection settings
cnx = st.connection("snowflake")
session = cnx.session()

# Load fruit names and API search terms
my_dataframe = session.table(
    "SMOOTHIES.PUBLIC.FRUIT_OPTIONS"
).select(
    col("FRUIT_NAME"),
    col("SEARCH_ON")
)

# Convert Snowpark DataFrame to Pandas
pd_df = my_dataframe.to_pandas()

# Display fruit options for debugging
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
    max_selections=5
)

# Retrieve nutrition information
if ingredients_list:
    for fruit_chosen in ingredients_list:
        search_on = pd_df.loc[
            pd_df["FRUIT_NAME"] == fruit_chosen,
            "SEARCH_ON"
        ].iloc[0]

        st.write(
            "The API search value for",
            fruit_chosen,
            "is",
            search_on
        )

        st.subheader(f"{fruit_chosen} Nutrition Information")

        try:
            response = requests.get(
                "https://my.smoothiefroot.com/api/fruit/"
                + requests.utils.quote(str(search_on), safe=""),
                timeout=10
            )

            if response.status_code == 200:
                nutrition_df = pd.json_normalize(response.json())
                st.dataframe(
                    nutrition_df,
                    use_container_width=True
                )
            elif response.status_code == 404:
                st.warning(
                    f"{fruit_chosen}: This fruit was not found in the API."
                )
            else:
                st.warning(
                    f"API returned HTTP {response.status_code} "
                    f"for {fruit_chosen}."
                )

        except requests.RequestException as error:
            st.warning(
                f"Could not retrieve nutrition data for "
                f"{fruit_chosen}: {error}"
            )

    st.write("Your ingredients:", ", ".join(ingredients_list))

# Submit order
if st.button("Submit Order"):
    if not name_on_order.strip():
        st.warning("Please enter your name.")
    elif not ingredients_list:
        st.warning("Please select at least one ingredient.")
    else:
        try:
            # Keep a trailing space after each ingredient.
            # This matches the expected DABW008 ingredient hash format.
            ingredients_string = "".join(
                fruit + " " for fruit in ingredients_list
            )

            session.sql(
                """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (INGREDIENTS, NAME_ON_ORDER)
                VALUES (?, ?)
                """,
                params=[
                    ingredients_string,
                    name_on_order.strip()
                ]
            ).collect()

            st.success(
                f"Your smoothie is ordered, "
                f"{name_on_order.strip()}!",
                icon="✅"
            )

        except Exception as error:
            st.error(f"Could not save your order: {error}")
