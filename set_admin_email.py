import os
import sys
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://croppulse_admin:Zxe2xNCZH4Wx1OC8AcZXUD1XIyAZcWGE@dpg-dbianulg1s2s73efl4m0-a/croppulse_demo"
engine = create_engine(DB_URL)
with engine.connect() as conn:
    # Set the role to admin for the given email
    conn.execute(text("UPDATE farmers SET role = 'admin' WHERE email = 'nkurunzizamodern@gmail.com'"))
    conn.commit()
    print('Updated role to admin for nkurunzizamodern@gmail.com')