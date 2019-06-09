from django.db import models
from django.db.backends.ddl_references import Columns, Statement, Table
from django.db.models.constraints import BaseConstraint


# Problems to resolve:
#  - The solution below won't work for unique_together, only if a
#    UniqueConstraint is added as it seems to be added before the FK
#    constraint.
#  - The solution below only works because the model with the fk constraint is
#    declared after the parent model, meaning the constraints are applied in
#    that order as well.
#  - Refer to referenced model as a string?


class ForeignKeyConstraint(BaseConstraint):
    fk_constraint = 'FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s)%(deferrable)s'

    def __init__(self, to_model, columns, to_columns, name):
        super().__init__(name)
        self.columns = columns
        self.to_columns = to_columns
        self.to_model = to_model

    def constraint_sql(self, model, schema_editor):
        # This is called if the constraint is added as part of the CreateModel
        # operation.  makemigrations doesn't appear to do this though.  Doing
        # this way will break if the referenced index hasn't been created yet
        # – this will happen in Django migrations as unique_together indexes
        # are deferred.
        return schema_editor.sql_constraint % {
            'name': schema_editor.quote_name(self.name),
            'constraint': self.fk_constraint % {
                'columns': self.columns,
                'to_model': self.to_model._meta.db_table,
                'to_columns': self.to_columns,
            },
        }

    def create_sql(self, model, schema_editor):
        # Called from the AddConstraint operation
        table = Table(model._meta.db_table, schema_editor.quote_name)
        columns = Columns(model._meta.db_table, self.columns, schema_editor.quote_name)
        to_columns = Columns(self.to_model._meta.db_table, self.to_columns, schema_editor.quote_name)
        to_table = Table(self.to_model._meta.db_table, schema_editor.quote_name)
        return Statement(
            schema_editor.sql_create_fk,
            table=table,
            name=self.name,
            column=columns,
            to_table=to_table,
            to_column=to_columns,
            deferrable='',
        )

    def remove_sql(self, model, schema_editor):
        # Called from the RemoveConstraint operation
        return schema_editor._delete_constraint_sql(schema_editor.sql_delete_constraint, model, self.name)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['columns'] = self.columns
        kwargs['to_columns'] = self.to_columns
        kwargs['to_model'] = self.to_model
        return path, args, kwargs


class Bar(models.Model):
    baz = models.IntegerField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('id', 'baz'),
                name='unique_id_and_baz',
            ),
        )


class Foo(models.Model):
    bar = models.ForeignKey(Bar, on_delete=models.CASCADE)
    baz = models.IntegerField()

    class Meta:
        constraints = (
            ForeignKeyConstraint(
                to_model=Bar,
                columns=('bar_id', 'baz'),
                to_columns=('id', 'baz'),
                name='composite_fk',
            ),
        )
