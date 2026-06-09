"""baseline

Revision ID: 6b3c3c59c3e3
Revises: 
Create Date: 2026-05-18 16:11:25.355296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import slidetap.database.types


revision: str = '6b3c3c59c3e3'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('dataset',
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('valid_attributes', sa.Boolean(), nullable=True),
    sa.Column('valid_items', sa.Boolean(), nullable=True),
    sa.Column('schema_uid', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_dataset_schema_uid'), 'dataset', ['schema_uid'], unique=False)
    op.create_table('mapper_group',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('default_enabled', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_mapper_group_name'), 'mapper_group', ['name'], unique=True)
    op.create_table('tag',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.Column('description', sa.String(length=512), nullable=True),
    sa.Column('color', sa.String(length=7), nullable=True),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('mapper',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('attribute_schema_uid', sa.Uuid(), nullable=False),
    sa.Column('root_attribute_schema_uid', sa.Uuid(), nullable=False),
    sa.Column('mapper_group_uid', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['mapper_group_uid'], ['mapper_group.uid'], ),
    sa.PrimaryKeyConstraint('uid'),
    sa.UniqueConstraint('attribute_schema_uid', 'root_attribute_schema_uid')
    )
    op.create_index(op.f('ix_mapper_attribute_schema_uid'), 'mapper', ['attribute_schema_uid'], unique=False)
    op.create_index(op.f('ix_mapper_mapper_group_uid'), 'mapper', ['mapper_group_uid'], unique=False)
    op.create_index(op.f('ix_mapper_name'), 'mapper', ['name'], unique=True)
    op.create_index(op.f('ix_mapper_root_attribute_schema_uid'), 'mapper', ['root_attribute_schema_uid'], unique=False)
    op.create_table('project',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('status', sa.Enum('IN_PROGRESS', 'COMPLETED', 'EXPORTING', 'EXPORT_COMPLETE', 'FAILED', 'DELETED', name='projectstatus'), nullable=False),
    sa.Column('valid_attributes', sa.Boolean(), nullable=True),
    sa.Column('locked', sa.Boolean(), nullable=False),
    sa.Column('root_schema_uid', sa.Uuid(), nullable=False),
    sa.Column('schema_uid', sa.Uuid(), nullable=False),
    sa.Column('default_batch_uid', sa.Uuid(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('dataset_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['dataset_uid'], ['dataset.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_project_schema_uid'), 'project', ['schema_uid'], unique=False)
    op.create_table('batch',
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('INITIALIZED', 'METADATA_SEARCHING', 'METADATA_SEARCH_COMPLETE', 'IMAGE_PRE_PROCESSING', 'IMAGE_PRE_PROCESSING_COMPLETE', 'IMAGE_POST_PROCESSING', 'IMAGE_POST_PROCESSING_COMPLETE', 'COMPLETED', 'IMAGE_STORING', 'FAILED', 'DELETED', name='batchstatus'), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('project_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['project_uid'], ['project.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('mapper_group_to_project',
    sa.Column('mapper_group_uid', sa.Uuid(), nullable=False),
    sa.Column('project_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['mapper_group_uid'], ['mapper_group.uid'], ),
    sa.ForeignKeyConstraint(['project_uid'], ['project.uid'], ),
    sa.PrimaryKeyConstraint('mapper_group_uid', 'project_uid')
    )
    op.create_table('mapping_item',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('mapper_uid', sa.Uuid(), nullable=False),
    sa.Column('expression', sa.String(length=128), nullable=False),
    sa.Column('attribute', slidetap.database.types.AttributeJson(), nullable=False),
    sa.Column('hits', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['mapper_uid'], ['mapper.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_mapping_item_mapper_uid'), 'mapping_item', ['mapper_uid'], unique=False)
    op.create_table('item',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('identifier', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('external_identifier', sa.String(length=128), nullable=True),
    sa.Column('pseudonym', sa.String(length=128), nullable=True),
    sa.Column('selected', sa.Boolean(), nullable=False),
    sa.Column('comment', sa.String(length=512), nullable=True),
    sa.Column('valid_attributes', sa.Boolean(), nullable=False),
    sa.Column('valid_relations', sa.Boolean(), nullable=False),
    sa.Column('valid_pseudonym', sa.Boolean(), nullable=False),
    sa.Column('item_value_type', sa.Enum('SAMPLE', 'IMAGE', 'ANNOTATION', 'OBSERVATION', name='itemvaluetype'), nullable=False),
    sa.Column('locked', sa.Boolean(), nullable=False),
    sa.Column('schema_uid', sa.Uuid(), nullable=False),
    sa.Column('dataset_uid', sa.Uuid(), nullable=False),
    sa.Column('batch_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['batch_uid'], ['batch.uid'], ),
    sa.ForeignKeyConstraint(['dataset_uid'], ['dataset.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_item_batch_uid'), 'item', ['batch_uid'], unique=False)
    op.create_index(op.f('ix_item_dataset_uid'), 'item', ['dataset_uid'], unique=False)
    op.create_index(op.f('ix_item_item_value_type'), 'item', ['item_value_type'], unique=False)
    op.create_index(op.f('ix_item_schema_uid'), 'item', ['schema_uid'], unique=False)
    op.create_table('attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('schema_uid', sa.Uuid(), nullable=False),
    sa.Column('valid', sa.Boolean(), nullable=False),
    sa.Column('display_value', sa.String(), nullable=True),
    sa.Column('mappable_value', sa.String(length=512), nullable=True),
    sa.Column('tag', sa.String(length=128), nullable=False),
    sa.Column('attribute_value_type', sa.Enum('STRING', 'DATETIME', 'NUMERIC', 'MEASUREMENT', 'CODE', 'ENUM', 'BOOLEAN', 'OBJECT', 'LIST', 'UNION', name='attributevaluetype'), nullable=False),
    sa.Column('read_only', sa.Boolean(), nullable=False),
    sa.Column('locked', sa.Boolean(), nullable=False),
    sa.Column('attribute_item_uid', sa.Uuid(), nullable=True),
    sa.Column('private_attribute_item_uid', sa.Uuid(), nullable=True),
    sa.Column('attribute_project_uid', sa.Uuid(), nullable=True),
    sa.Column('private_attribute_project_uid', sa.Uuid(), nullable=True),
    sa.Column('attribute_dataset_uid', sa.Uuid(), nullable=True),
    sa.Column('private_attribute_dataset_uid', sa.Uuid(), nullable=True),
    sa.Column('mapping_item_uid', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_dataset_uid'], ['dataset.uid'], ),
    sa.ForeignKeyConstraint(['attribute_item_uid'], ['item.uid'], ),
    sa.ForeignKeyConstraint(['attribute_project_uid'], ['project.uid'], ),
    sa.ForeignKeyConstraint(['mapping_item_uid'], ['mapping_item.uid'], ),
    sa.ForeignKeyConstraint(['private_attribute_dataset_uid'], ['dataset.uid'], ),
    sa.ForeignKeyConstraint(['private_attribute_item_uid'], ['item.uid'], ),
    sa.ForeignKeyConstraint(['private_attribute_project_uid'], ['project.uid'], ),
    sa.PrimaryKeyConstraint('uid'),
    sa.UniqueConstraint('schema_uid', 'attribute_item_uid', 'private_attribute_item_uid', 'attribute_project_uid', 'private_attribute_project_uid', 'attribute_dataset_uid', 'private_attribute_dataset_uid', 'mapping_item_uid')
    )
    op.create_index(op.f('ix_attribute_attribute_dataset_uid'), 'attribute', ['attribute_dataset_uid'], unique=False)
    op.create_index(op.f('ix_attribute_attribute_item_uid'), 'attribute', ['attribute_item_uid'], unique=False)
    op.create_index(op.f('ix_attribute_attribute_project_uid'), 'attribute', ['attribute_project_uid'], unique=False)
    op.create_index(op.f('ix_attribute_attribute_value_type'), 'attribute', ['attribute_value_type'], unique=False)
    op.create_index(op.f('ix_attribute_mapping_item_uid'), 'attribute', ['mapping_item_uid'], unique=False)
    op.create_index(op.f('ix_attribute_private_attribute_dataset_uid'), 'attribute', ['private_attribute_dataset_uid'], unique=False)
    op.create_index(op.f('ix_attribute_private_attribute_item_uid'), 'attribute', ['private_attribute_item_uid'], unique=False)
    op.create_index(op.f('ix_attribute_private_attribute_project_uid'), 'attribute', ['private_attribute_project_uid'], unique=False)
    op.create_index(op.f('ix_attribute_tag'), 'attribute', ['tag'], unique=False)
    op.create_table('image',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('folder_path', sa.String(length=512), nullable=True),
    sa.Column('thumbnail_path', sa.String(length=512), nullable=True),
    sa.Column('status', sa.Enum('NOT_STARTED', 'DOWNLOADING', 'DOWNLOADING_FAILED', 'DOWNLOADED', 'PRE_PROCESSING', 'PRE_PROCESSING_FAILED', 'PRE_PROCESSED', 'POST_PROCESSING', 'POST_PROCESSING_FAILED', 'POST_PROCESSED', name='imagestatus'), nullable=False),
    sa.Column('status_message', sa.String(length=512), nullable=True),
    sa.Column('format', sa.Enum('DICOM_WSI', 'OTHER_WSI', 'DICOM_SINGLE_FRAME', 'OTHER_SINGLE_FRAME', name='imageformat'), nullable=False),
    sa.ForeignKeyConstraint(['uid'], ['item.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('item_to_tag',
    sa.Column('item_uid', sa.Uuid(), nullable=False),
    sa.Column('tag_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['item_uid'], ['item.uid'], ),
    sa.ForeignKeyConstraint(['tag_uid'], ['tag.uid'], ),
    sa.PrimaryKeyConstraint('item_uid', 'tag_uid')
    )
    op.create_table('metadata_search_item',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('batch_uid', sa.Uuid(), nullable=False),
    sa.Column('identifier', sa.String(length=128), nullable=False),
    sa.Column('schema_uid', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('NOT_STARTED', 'FAILED', 'COMPLETE', name='metadataimportstatus'), nullable=False),
    sa.Column('message', sa.String(length=512), nullable=True),
    sa.Column('item_uid', sa.Uuid(), nullable=True),
    sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['batch_uid'], ['batch.uid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_uid'], ['item.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_metadata_search_item_batch_uid'), 'metadata_search_item', ['batch_uid'], unique=False)
    op.create_index(op.f('ix_metadata_search_item_schema_uid'), 'metadata_search_item', ['schema_uid'], unique=False)
    op.create_table('sample',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['uid'], ['item.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('annotation',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('image_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['image_uid'], ['image.uid'], ),
    sa.ForeignKeyConstraint(['uid'], ['item.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('attribute_list',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', slidetap.database.types.AttributeListJson(), nullable=True),
    sa.Column('updated_value', slidetap.database.types.AttributeListJson(), nullable=True),
    sa.Column('mapped_value', slidetap.database.types.AttributeListJson(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('attribute_union',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', slidetap.database.types.AttributeJson(), nullable=True),
    sa.Column('updated_value', slidetap.database.types.AttributeJson(), nullable=True),
    sa.Column('mapped_value', slidetap.database.types.AttributeJson(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('boolean_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', sa.Boolean(), nullable=True),
    sa.Column('updated_value', sa.Boolean(), nullable=True),
    sa.Column('mapped_value', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('code_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', slidetap.database.types.CodeJson(), nullable=True),
    sa.Column('updated_value', slidetap.database.types.CodeJson(), nullable=True),
    sa.Column('mapped_value', slidetap.database.types.CodeJson(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('datetime_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', sa.DateTime(), nullable=True),
    sa.Column('updated_value', sa.DateTime(), nullable=True),
    sa.Column('mapped_value', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('enum_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', sa.String(length=128), nullable=True),
    sa.Column('updated_value', sa.String(length=128), nullable=True),
    sa.Column('mapped_value', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('image_file',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('filename', sa.String(length=512), nullable=False),
    sa.Column('image_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['image_uid'], ['image.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('measurement_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', slidetap.database.types.MeasurementJson(), nullable=True),
    sa.Column('updated_value', slidetap.database.types.MeasurementJson(), nullable=True),
    sa.Column('mapped_value', slidetap.database.types.MeasurementJson(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('number_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', sa.Float(), nullable=True),
    sa.Column('updated_value', sa.Float(), nullable=True),
    sa.Column('mapped_value', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('object_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', slidetap.database.types.AttributeDictJson(), nullable=True),
    sa.Column('updated_value', slidetap.database.types.AttributeDictJson(), nullable=True),
    sa.Column('mapped_value', slidetap.database.types.AttributeDictJson(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('sample_to_image',
    sa.Column('sample_uid', sa.Uuid(), nullable=False),
    sa.Column('image_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['image_uid'], ['image.uid'], ),
    sa.ForeignKeyConstraint(['sample_uid'], ['sample.uid'], ),
    sa.PrimaryKeyConstraint('sample_uid', 'image_uid')
    )
    op.create_table('sample_to_sample',
    sa.Column('parent_uid', sa.Uuid(), nullable=False),
    sa.Column('child_uid', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['child_uid'], ['sample.uid'], ),
    sa.ForeignKeyConstraint(['parent_uid'], ['sample.uid'], ),
    sa.PrimaryKeyConstraint('parent_uid', 'child_uid')
    )
    op.create_table('string_attribute',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('original_value', sa.String(), nullable=True),
    sa.Column('updated_value', sa.String(), nullable=True),
    sa.Column('mapped_value', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['attribute.uid'], ),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('observation',
    sa.Column('uid', sa.Uuid(), nullable=False),
    sa.Column('image_uid', sa.Uuid(), nullable=True),
    sa.Column('sample_uid', sa.Uuid(), nullable=True),
    sa.Column('annotation_uid', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['annotation_uid'], ['annotation.uid'], ),
    sa.ForeignKeyConstraint(['image_uid'], ['image.uid'], ),
    sa.ForeignKeyConstraint(['sample_uid'], ['sample.uid'], ),
    sa.ForeignKeyConstraint(['uid'], ['item.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uid')
    )


def downgrade() -> None:
    op.drop_table('observation')
    op.drop_table('string_attribute')
    op.drop_table('sample_to_sample')
    op.drop_table('sample_to_image')
    op.drop_table('object_attribute')
    op.drop_table('number_attribute')
    op.drop_table('measurement_attribute')
    op.drop_table('image_file')
    op.drop_table('enum_attribute')
    op.drop_table('datetime_attribute')
    op.drop_table('code_attribute')
    op.drop_table('boolean_attribute')
    op.drop_table('attribute_union')
    op.drop_table('attribute_list')
    op.drop_table('annotation')
    op.drop_table('sample')
    op.drop_index(op.f('ix_metadata_search_item_schema_uid'), table_name='metadata_search_item')
    op.drop_index(op.f('ix_metadata_search_item_batch_uid'), table_name='metadata_search_item')
    op.drop_table('metadata_search_item')
    op.drop_table('item_to_tag')
    op.drop_table('image')
    op.drop_index(op.f('ix_attribute_tag'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_private_attribute_project_uid'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_private_attribute_item_uid'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_private_attribute_dataset_uid'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_mapping_item_uid'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_attribute_value_type'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_attribute_project_uid'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_attribute_item_uid'), table_name='attribute')
    op.drop_index(op.f('ix_attribute_attribute_dataset_uid'), table_name='attribute')
    op.drop_table('attribute')
    op.drop_index(op.f('ix_item_schema_uid'), table_name='item')
    op.drop_index(op.f('ix_item_item_value_type'), table_name='item')
    op.drop_index(op.f('ix_item_dataset_uid'), table_name='item')
    op.drop_index(op.f('ix_item_batch_uid'), table_name='item')
    op.drop_table('item')
    op.drop_index(op.f('ix_mapping_item_mapper_uid'), table_name='mapping_item')
    op.drop_table('mapping_item')
    op.drop_table('mapper_group_to_project')
    op.drop_table('batch')
    op.drop_index(op.f('ix_project_schema_uid'), table_name='project')
    op.drop_table('project')
    op.drop_index(op.f('ix_mapper_root_attribute_schema_uid'), table_name='mapper')
    op.drop_index(op.f('ix_mapper_name'), table_name='mapper')
    op.drop_index(op.f('ix_mapper_mapper_group_uid'), table_name='mapper')
    op.drop_index(op.f('ix_mapper_attribute_schema_uid'), table_name='mapper')
    op.drop_table('mapper')
    op.drop_table('tag')
    op.drop_index(op.f('ix_mapper_group_name'), table_name='mapper_group')
    op.drop_table('mapper_group')
    op.drop_index(op.f('ix_dataset_schema_uid'), table_name='dataset')
    op.drop_table('dataset')
