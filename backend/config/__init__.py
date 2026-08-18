"""Django project configuration.

PyMySQL is optional so a local SQLite install does not require the MySQL driver.
"""

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass

