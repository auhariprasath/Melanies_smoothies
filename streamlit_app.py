
import base64
import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col
from cryptography.hazmat.primitives import serialization

st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered",
)

st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom smoothie!")

name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your smoothie will be:", name_on_order)


@st.cache_resource
def create_session():
    cfg = st.secrets["connections"]["snowflake"]

    # Decode the Base64-encoded private key from Streamlit Secrets
    private_key_bytes = base64.b64decode(cfg["private_key_b64"])

    private_key = serialization.load_pem_private_key(
        private_key_bytes,
        password=None,
    )

    # Convert the private key to the DER format Snowflake expects
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
