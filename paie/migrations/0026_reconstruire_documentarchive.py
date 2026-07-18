from django.db import migrations

SQL_DROP = "DROP TABLE IF EXISTS paie_documentarchive;"

SQL_CREATE = """
CREATE TABLE "paie_documentarchive" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "type_doc" varchar(50) NOT NULL,
    "libelle" varchar(200) NOT NULL,
    "cle" varchar(200) NOT NULL,
    "contenu" BLOB NOT NULL,
    "nom_fichier" varchar(200) NOT NULL,
    "content_type" varchar(100) NOT NULL,
    "mois" integer NULL,
    "annee" integer NULL,
    "cree_le" datetime NOT NULL,
    "modifie_le" datetime NOT NULL,
    "annee_creation" integer NOT NULL,
    "employe_id" bigint NULL REFERENCES "paie_employe" ("id") DEFERRABLE INITIALLY DEFERRED,
    "employeur_id" bigint NOT NULL REFERENCES "paie_employeur" ("id") DEFERRABLE INITIALLY DEFERRED
);
"""

SQL_INDEX = [
    'CREATE INDEX "paie_documentarchive_cle_idx" ON "paie_documentarchive" ("cle");',
    'CREATE INDEX "paie_documentarchive_employe_id_idx" ON "paie_documentarchive" ("employe_id");',
    'CREATE INDEX "paie_documentarchive_employeur_id_idx" ON "paie_documentarchive" ("employeur_id");',
]


def reconstruire(apps, schema_editor):
    schema_editor.execute(SQL_DROP)
    schema_editor.execute(SQL_CREATE)
    for sql in SQL_INDEX:
        schema_editor.execute(sql)


def inverse(apps, schema_editor):
    # Pas de retour arrière utile : la table était déjà incohérente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('paie', '0025_jourferie_alter_conge_options_remove_conge_annee_and_more'),
    ]

    operations = [
        migrations.RunPython(reconstruire, inverse),
    ]
