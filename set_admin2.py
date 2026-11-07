import sys
from sqlalchemy import create_engine, text

URL = "postgresql+psycopg://croppulse_admin:Zxe2xNCZH4Wx1OC8AcZXUD1XIyAZcWGE@dpg-dbianulg1s2s73efl4m0-a/croppulse_demo"
engine = create_engine(URL)
with engine.connect() as conn:
    conn.execute(text("UPDATE farmers SET role = 'admin' WHERE email = 'nkurunzizamodern2@gmail.com'"))
    conn.commit()
    print('Updated role to admin for nkurunzizamodern2@gmail.com')