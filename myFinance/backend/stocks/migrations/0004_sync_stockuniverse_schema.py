from django.db import migrations

FIELDS = ['nse_code','bse_code','yfinance_symbol','series','isin_code','source_file','is_active','created_at','updated_at']

def sync_stockuniverse_schema(apps, schema_editor):
    model = apps.get_model('stocks', 'StockUniverse')
    table_name = model._meta.db_table
    connection = schema_editor.connection
    if table_name not in set(connection.introspection.table_names()):
        return
    with connection.cursor() as cursor:
        columns = {column.name for column in connection.introspection.get_table_description(cursor, table_name)}
    for field_name in FIELDS:
        if field_name not in columns:
            field = model._meta.get_field(field_name)
            schema_editor.add_field(model, field)
            columns.add(field.column)

def noop_reverse(apps, schema_editor):
    return

class Migration(migrations.Migration):
    dependencies = [('stocks', '0003_stockuniverse')]
    operations = [migrations.RunPython(sync_stockuniverse_schema, noop_reverse)] 
