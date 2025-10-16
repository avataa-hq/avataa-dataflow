# from typing import Union
#
# from sqlalchemy import select
# from sqlalchemy.exc import NoResultFound
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from airflow_source_managers.database.schemas import SourceGroup, Source
# from v3.file_server.minio_client_manager import minio_client
# from v3.routers.sources.models.api_model import APIModelCreate
# from v3.routers.sources.models.db_model import DBModelCreate
# from v3.routers.sources.models.file_model import SFTPModelCreate, FileImportType
# from v3.routers.sources.models.general_model import SourceType
# from v3.routers.sources.sources_managers.file_manager import ManualFileSourceManager
#
#
# async def check_group_exists(session: AsyncSession, group_id: int):
#     try:
#         stmt = select(SourceGroup.id).where(SourceGroup.id == group_id)
#         response = await session.scalars(stmt)
#         response.one()
#     except NoResultFound:
#         raise ValueError(f'Source group with id={group_id} does not exist!')
#
#
# def read_file(file):
#     contents = file.file.read()
#     file.file.close()
#
#     return contents
#
#
# async def check_source_name_in_group_exists(session: AsyncSession, group_id: int, source_name: str):
#     stmt = select(Source.id).where(Source.group_id == group_id, Source.name == source_name)
#     res = await session.execute(stmt)
#     res = res.scalars().first()
#     if res is not None:
#         raise ValueError(f"Source named '{source_name}' already exists in group with id={group_id}!")
#
#
# async def check_source_exists(session: AsyncSession, source_id: int):
#     """Raises error if Source with id={source_id} does not exist, otherwise return Source instance"""
#     stmt = select(Source).where(Source.id == source_id)
#     res = await session.scalars(stmt)
#     res = res.first()
#     if res is None:
#         raise ValueError(f"Source with id={source_id} does not exist!")
#     return res
#
#
# async def update_for_simple_types(source_id: int,
#                                   source_model: Union[SFTPModelCreate, DBModelCreate, APIModelCreate],
#                                   session: AsyncSession):
#     """Returns updated source if all conditions is ok. Use only for update models:
#     [SFTPModelCreate, DBModelCreate, APIModelCreate]"""
#     await check_group_exists(session, source_model.group_id)
#     # check if source name is unique across the group
#     stmt = select(Source).where(Source.name == source_model.name,
#                                 Source.group_id == source_model.group_id,
#                                 Source.id != source_id)
#     source_from_db = await session.execute(stmt)
#     source_from_db = source_from_db.scalars().first()
#     if source_from_db is not None:
#         raise ValueError(f"Source named '{source_model.name}' already exists in"
#                          f" group with id={source_model.group_id}!")
#
#     source_to_update = await check_source_exists(session, source_id)
#
#     if source_to_update.con_type == SourceType.FILE.value:
#         decoded_data = source_to_update.decoded_data()
#         if decoded_data['con_data']['import_type'] == FileImportType.MANUAL.value:
#             source_manager = ManualFileSourceManager(source_id=source_to_update.id,
#                                                      con_data=decoded_data['con_data'],
#                                                      client=minio_client())
#             source_manager.delete_file_from_minio()
#
#     for k, v in source_model.dict(exclude_unset=True).items():
#         setattr(source_to_update, k, v)
#
#     session.add(source_to_update)
#     await session.commit()
#     await session.refresh(source_to_update)
#     return source_to_update
#
#
# def get_user_id_from_request(request):
#     """Returns user id from request, otherwise return None"""
#     user_info = getattr(request, 'user_info', None)
#     if user_info is None:
#         return None
#
#     user_decoded_token = user_info.get('credentials')
#     if user_decoded_token is None:
#         return None
#     sub = user_decoded_token.get('sub')
#
#     if sub is None:
#         return None
#     return sub
