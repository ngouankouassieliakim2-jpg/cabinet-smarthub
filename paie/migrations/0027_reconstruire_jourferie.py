from django.db import migrations

SQL_DROP = "DROP TABLE IF EXISTS paie_jourferie;"

SQL_CREATE_SQLITE = """
CREATE TABLE "paie_jourferie" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "date" date NOT NULL UNIQUE,
    "libelle" varchar(100) NOT NULL
);
"""

SQL_CREATE_POSTGRESQL = """
CREATE TABLE "paie_jourferie" (
    "id" serial NOT NULL PRIMARY KEY,
    "date" date NOT NULL UNIQUE,
    "libelle" varchar(100) NOT NULL
);
"""


def reconstruire(apps, schema_editor):
    schema_editor.execute(SQL_DROP)
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL_CREATE_POSTGRESQL)
    else:
        schema_editor.execute(SQL_CREATE_SQLITE)


def inverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('paie', '0026_reconstruire_documentarchive'),
    ]

    operations = [
        migrations.RunPython(reconstruire, inverse),
    ]
