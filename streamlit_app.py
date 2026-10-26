
import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col

st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered"
)

st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom smoothie!")

name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your smoothie will be:", name_on_order)


@st.cache_resource
def create_session():
    connection_parameters = dict(
        st.secrets["connections"]["snowflake"]
    )

    # Explicit Snowflake connection settings
    connection_parameters["account"] = "IXFHMEC-EPB48038"
    connection_parameters["user"] = "HARI24PRASATH2005"
    connection_parameters["database"] = "SMOOTHIES"
    connection_parameters["schema"] = "PUBLIC"
    connection_parameters["warehouse"] = "COMPUTE_WH"
    connection_parameters["role"] = "SYSADMIN"

    return Session.builder.configs(
        connection_parameters
    ).create()


try:
    session = create_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col("FRUIT_NAME"))
        .collect()
    )

    fruit_options = [
        row["FRUIT_NAME"] for row in fruit_rows
    ]

    if not fruit_options:
        st.warning(
            "No fruits found. Check the FRUIT_OPTIONS table."
        )
    else:
        ingredients_list = st.multiselect(
            "Choose up to 5 ingredients:",
            options=fruit_options,
            max_selections=5
        )

        if st.button("Submit Order", type="primary"):
            if not name_on_order.strip():
                st.warning("Please enter your name.")

            elif not ingredients_list:
                st.warning("Please choose at least one fruit.")

            else:
                ingredients_string = " ".join(
                    ingredients_list
                )

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
                    f"Your smoothie is ordered, "
                    f"{name_on_order.strip()}!",
                    icon="✅"
                )

except Exception as e:
    st.error("Unable to connect to Snowflake or load fruits.")
    st.caption(f"Error details: {str(e)}")
