from django.db import migrations

SQL_DROP = "DROP TABLE IF EXISTS paie_jourferie;"

SQL_CREATE = """
CREATE TABLE "paie_jourferie" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "date" date NOT NULL UNIQUE,
    "libelle" varchar(100) NOT NULL
);
"""

def reconstruire(apps, schema_editor):
    schema_editor.execute(SQL_DROP)
    schema_editor.execute(SQL_CREATE)


def inverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('paie', '0026_reconstruire_documentarchive'),
    ]

    operations = [
        migrations.RunPython(reconstruire, inverse),
    ]
