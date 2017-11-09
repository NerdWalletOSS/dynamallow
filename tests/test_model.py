import os
import pytest

from dynamorm.model import DynaModel, GlobalIndex, LocalIndex, ProjectAll, ProjectInclude
from dynamorm.exceptions import InvalidSchemaField, MissingTableAttribute, DynaModelException
from dynamorm.types import OneToMany, OneToOne  # , ManyToMany

if 'marshmallow' in (os.getenv('SERIALIZATION_PKG') or ''):
    from marshmallow.fields import String, Decimal as Number
else:
    from schematics.types import StringType as String, IntType as Number

try:
    from unittest.mock import MagicMock, call
except ImportError:
    from mock import MagicMock, call


def test_missing_inner_classes():
    """Classes must have both a Table and Schema inner class"""
    with pytest.raises(DynaModelException):
        class Model(DynaModel):
            pass


def test_missing_inner_schema_class():
    """Classes must have an inner Schema class"""
    with pytest.raises(DynaModelException):
        class Model(DynaModel):
            class Table:
                pass


def test_missing_inner_table_class():
    """Classes must have an inner Table class"""
    with pytest.raises(DynaModelException):
        class Model(DynaModel):
            class Schema:
                pass


def test_parent_inner_classes():
    class Parent(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            read = 1
            write = 1

        class Schema:
            foo = String(required=True)

    class Child(Parent):
        pass

    assert Child.Table is Parent.Table


def test_table_validation():
    """Defining a model with missing table attributes should raise exceptions"""
    with pytest.raises(MissingTableAttribute):
        class Model(DynaModel):
            class Table:
                name = 'table'

            class Schema:
                foo = String(required=True)


def test_table_create_validation():
    """You cannot create a table that is missing read/write attrs"""
    with pytest.raises(MissingTableAttribute):
        class Model(DynaModel):
            class Table:
                name = 'table'
                hash_key = 'foo'
                read = 5

            class Schema:
                foo = String(required=True)

        Model.Table.create_table()

    with pytest.raises(MissingTableAttribute):
        class Model(DynaModel):
            class Table:
                name = 'table'
                hash_key = 'foo'
                write = 5

            class Schema:
                foo = String(required=True)

        Model.Table.create_table()

    with pytest.raises(MissingTableAttribute):
        class Model(DynaModel):
            class Table:
                name = 'table'
                hash_key = 'foo'

            class Schema:
                foo = String(required=True)

        Model.Table.create_table()


def test_invalid_hash_key():
    """Defining a model where ``hash_key`` in Table points to an invalid field should raise InvalidSchemaField"""
    with pytest.raises(InvalidSchemaField):
        class Model(DynaModel):
            class Table:
                name = 'table'
                hash_key = 'foo'
                read = 1
                write = 1

            class Schema:
                bar = String(required=True)


def test_invalid_range_key():
    """Defining a model where ``range_key`` in Table points to an invalid field should raise InvalidSchemaField"""
    with pytest.raises(InvalidSchemaField):
        class Model(DynaModel):
            class Table:
                name = 'table'
                hash_key = 'foo'
                range_key = 'bar'
                read = 1
                write = 1

            class Schema:
                foo = String(required=True)
                baz = String(required=True)


def test_number_hash_key():
    """Test a number hash key and ensure the dynamo type gets set correctly"""
    class Model(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            read = 1
            write = 1

        class Schema:
            foo = Number(required=True)
            baz = String(required=True)

    model = Model(foo=1, baz='foo')
    assert model.Table.attribute_definitions == [{'AttributeName': 'foo', 'AttributeType': 'N'}]


def test_index_setup():
    """Ensure our index objects are setup & transformed correctly by our meta class"""
    class Model(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            range_key = 'bar'
            read = 1
            write = 1

        class Index(GlobalIndex):
            name = 'test-idx'
            hash_key = 'foo'
            range_key = 'bar'
            projection = ProjectAll()

        class Schema:
            foo = String(required=True)
            bar = String(required=True)

    model = Model(foo='hi', bar='there')

    assert 'test-idx' in model.Table.indexes
    assert model.Index.index is model.Table.indexes['test-idx']
    assert model.Index.index.table is model.Table

    assert model.Index.index.schema is model.Schema

    # this gets automatically set during initialization, since read is an optional parameter
    assert model.Index.index.read is None


def test_invalid_indexes():
    """Ensure validation happens for indexes"""
    for idx in (GlobalIndex, LocalIndex):
        with pytest.raises(MissingTableAttribute):
            class Model1(DynaModel):
                class Table:
                    name = 'table'
                    hash_key = 'foo'
                    range_key = 'bar'
                    read = 1
                    write = 1

                class Index(idx):
                    name = 'test-idx'
                    # missing hash_key
                    range_key = 'bar'
                    projection = ProjectAll()

                class Schema:
                    foo = String(required=True)
                    bar = String(required=True)

        with pytest.raises(MissingTableAttribute):
            class Model2(DynaModel):
                class Table:
                    name = 'table'
                    hash_key = 'foo'
                    range_key = 'bar'
                    read = 1
                    write = 1

                class Index(idx):
                    name = 'test-idx'
                    hash_key = 'foo'
                    range_key = 'bar'
                    # no projection

                class Schema:
                    foo = String(required=True)
                    bar = String(required=True)

        with pytest.raises(InvalidSchemaField):
            class Model3(DynaModel):
                class Table:
                    name = 'table'
                    hash_key = 'foo'
                    range_key = 'bar'
                    read = 1
                    write = 1

                class Index(idx):
                    name = 'test-idx'
                    hash_key = 'foo'
                    # no key named baz
                    range_key = 'baz'
                    projection = ProjectAll()

                class Schema:
                    foo = String(required=True)
                    bar = String(required=True)

        with pytest.raises(InvalidSchemaField):
            class Model4(DynaModel):
                class Table:
                    name = 'table'
                    hash_key = 'foo'
                    range_key = 'bar'
                    read = 1
                    write = 1

                class Index(idx):
                    name = 'test-idx'
                    # no key named baz
                    hash_key = 'baz'
                    range_key = 'bar'
                    projection = ProjectAll()

                class Schema:
                    foo = String(required=True)
                    bar = String(required=True)


def test_update_table(dynamo_local):
    class TableV1(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            range_key = 'bar'
            read = 5
            write = 5

        class Schema:
            foo = String(required=True)
            bar = String(required=True)
            baz = String(required=True)
            bbq = String(required=True)

    class TableV2(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            range_key = 'bar'
            read = 10
            write = 10

        class Index1(GlobalIndex):
            name = 'index1'
            hash_key = 'baz'
            range_key = 'bar'
            projection = ProjectAll()
            read = 5
            write = 5

        class Index2(GlobalIndex):
            name = 'index2'
            hash_key = 'bbq'
            range_key = 'bar'
            projection = ProjectAll()
            read = 5
            write = 5

        class Schema:
            foo = String(required=True)
            bar = String(required=True)
            baz = String(required=True)
            bbq = String(required=True)

    class TableV3(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            range_key = 'bar'
            read = 10
            write = 10

        class Index2(GlobalIndex):
            name = 'index2'
            hash_key = 'bbq'
            range_key = 'bar'
            projection = ProjectAll()
            read = 5
            write = 5

        class Schema:
            foo = String(required=True)
            bar = String(required=True)
            baz = String(required=True)
            bbq = String(required=True)

    TableV1.Table.create_table()

    # updating to v2 should result in 3 changes
    # * changing throughput
    # * adding index1
    # * adding index2
    assert TableV2.Table.update_table() == 3

    # updating to v2 result in 1 change
    # * deleting index 1
    assert TableV3.Table.update_table() == 1

    # should now be a no-op
    assert TableV3.Table.update_table() == 0


def test_sparse_indexes(dynamo_local):
    class MyModel(DynaModel):
        class Table:
            name = 'mymodel'
            hash_key = 'foo'
            read = 10
            write = 10

        class Index1(GlobalIndex):
            name = 'index1'
            hash_key = 'bar'
            read = 10
            write = 10
            projection = ProjectInclude('foo', 'bar')

        class Schema:
            foo = String(required=True)
            bar = String(required=True)
            baz = String(required=True)
            bbq = String(required=True)

    MyModel.Table.create_table()
    MyModel.put_batch(
        {'foo': '1', 'bar': '1', 'baz': '1', 'bbq': '1'},
        {'foo': '2', 'bar': '2', 'baz': '2', 'bbq': '2'},
    )

    items = list(MyModel.Index1.query(bar='2'))
    assert len(items) == 1
    assert items[0].foo == '2'


def test_partial_save(TestModel, TestModel_entries, dynamo_local):
    def get_first():
        first = TestModel.get(foo='first', bar='one')
        first.Table = MagicMock()
        first.Table.hash_key = 'foo'
        first.Table.range_key = 'bar'
        return first

    # the first time to a non-partial save and put should be called
    first = get_first()
    first.save()
    assert first.Table.put.called_once()
    assert first.Table.update.not_called()

    # next do a partial save without any changed and again with a change
    # put should not be called, and update should only be called once dispite save being called twice
    first = get_first()
    first.save(partial=True)
    first.baz = 'changed'
    first.save(partial=True)
    assert first.Table.put.not_called()
    assert first.Table.update.called_with(
        call(conditions=None, update_item_kwargs=None, baz='changed'),
    )


def test_explicit_schema_parents():
    """Inner Schema classes should be able to have explicit parents"""
    class Mixin(object):
        is_mixin = True

    class Model(DynaModel):
        class Table:
            name = 'table'
            hash_key = 'foo'
            read = 1
            write = 1

        class Schema(Mixin):
            foo = Number(required=True)
            baz = String(required=True)

    assert Model.Schema.is_mixin is True
    assert Model.Schema.dynamorm_fields()


def test_relationship_one_to_many(request, dynamo_local):
    """A Parent has many Child(ren)"""
    class Child(DynaModel):
        class Table:
            name = 'child'
            hash_key = 'name'
            read = 1
            write = 1

        class Schema:
            name = String(required=True)
            parent = OneToOne('Parent')

    class Parent(DynaModel):
        class Table:
            name = 'parent'
            hash_key = 'name'
            read = 1
            write = 1

        class Schema:
            name = String(required=True)
            children = OneToMany('Child')

    Child.Table.create()
    Parent.Table.create()
    request.addfinalizer(Child.Table.delete)
    request.addfinalizer(Parent.Table.delete)

    # first do some "raw" testing by inserting the correct values by hand
    Child.put_batch(
        {'name': 'kearney', 'parent_id': {'name': 'mom1'}},
        {'name': 'dolph', 'parent_id': {'name': 'mom1'}},
        {'name': 'jimbo', 'parent_id': {'name': 'mom2'}},
    )

    Parent.put_batch(
        {'name': 'mom1', 'children_id': [{'name': 'kearney'}, {'name': 'dolph'}]},
        {'name': 'mom2', 'children_id': [{'name': 'jimbo'}]},
    )

    kearney = Child.get(name='kearney')
    dolph = Child.get(name='dolph')
    jimbo = Child.get(name='jimbo')

    mom1 = Parent.get(name='mom1')
    mom2 = Parent.get(name='mom2')

    assert kearney.parent.name == dolph.parent.name == mom1.name
    assert jimbo.parent.name == mom2.name

    assert sorted([kid.name for kid in mom1.children]) == [dolph.name, kearney.name]
    assert [kid.name for kid in mom2.children] == [jimbo.name]

    # next, test mutating objects
    martin = Child(name='martin')
    martin.save()

    mom2.children.append(martin)
    mom2.save()

    mom2 = Parent.get(name='mom2', consistent=True)
    assert [kid.name for kid in mom2.children] == [jimbo.name, martin.name]

    martin = Child.get(name='martin')
    assert martin.parent.name == mom2.name


def test_relationship_one_to_one(request, dynamo_local):
    class Child(DynaModel):
        class Table:
            name = 'child'
            hash_key = 'name'
            range_key = 'age'
            read = 1
            write = 1

        class Schema:
            name = String(required=True)
            age = Number(required=True)
            parent = OneToOne('Parent')

    class Parent(DynaModel):
        class Table:
            name = 'parent'
            hash_key = 'name'
            read = 1
            write = 1

        class Schema:
            name = String(required=True)
            child = OneToOne('Child')

    Child.Table.create()
    Parent.Table.create()
    request.addfinalizer(Child.Table.delete)
    request.addfinalizer(Parent.Table.delete)

    Child.put_batch(
        {'name': 'kearney', 'age': 13, 'parent_id': {'name': 'mom1'}},
        {'name': 'dolph', 'age': 14, 'parent_id': {'name': 'mom2'}},
    )

    Parent.put_batch(
        {'name': 'mom1', 'child_id': {'name': 'kearney', 'age': 13}},
        {'name': 'mom2', 'child_id': {'name': 'dolph', 'age': 14}},
    )
    kearney = Child.get(name='kearney', age=13)
    dolph = Child.get(name='dolph', age=14)

    mom1 = Parent.get(name='mom1')
    mom2 = Parent.get(name='mom2')

    assert kearney.parent.name == mom1.name
    assert dolph.parent.name == mom2.name

    assert mom1.child.name == kearney.name
    assert mom2.child.name == dolph.name

    # Test assigning the relationship
    mom2.child = kearney
    mom2.save()

    assert Parent.get(name='mom2', consistent=True).child_id == {'name': 'kearney', 'age': 13}
