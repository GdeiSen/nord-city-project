import logging
from typing import Type, TypeVar, Dict, Optional
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
RepoType = TypeVar("RepoType")

class GenericRepository:
    """
    A generic repository providing standard CRUD operations for a specific
    SQLAlchemy model. This class should be instantiated for each model.
    """
    def __init__(self, model: Type[ModelType]):
        """
        Initializes the repository for a given SQLAlchemy model.

        Args:
            model: The SQLAlchemy model class this repository will manage.
        """
        self.model = model
        # The primary key column is determined dynamically for generic operations.
        # This assumes a single-column primary key, commonly named 'id'.
        self.pk_column = getattr(self.model, 'id', None)
        if self.pk_column is None:
            logger.warning(
                f"Model {self.model.__name__} does not have an 'id' attribute for PK. "
                f"Operations like get_by_id may fail if not overridden."
            )

    async def create(self, session, *, obj_in: ModelType) -> Optional[ModelType]:
        """
        Creates a new model instance in the database.

        Args:
            session: The active SQLAlchemy async session.
            obj_in: The SQLAlchemy model instance to create.

        Returns:
            The created model instance or None on failure.
        """
        try:
            session.add(obj_in)
            await session.commit()
            await session.refresh(obj_in)
            return obj_in
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}", exc_info=True)
            raise

    async def get_by_id(self, session, *, entity_id: int) -> Optional[ModelType]:
        """
        Retrieves a model instance by its primary key.

        Args:
            session: The active SQLAlchemy async session.
            entity_id: The primary key of the entity.

        Returns:
            The model instance or None if not found.
        """
        if self.pk_column is None:
            logger.error(f"Cannot get by ID: No primary key 'id' found on {self.model.__name__}.")
            raise Exception(f"No primary key 'id' found on {self.model.__name__}.")
        try:
            return await session.get(self.model, entity_id)
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {entity_id}: {e}", exc_info=True)
            raise

    async def get_all(self, session) -> list[ModelType]:
        """
        Retrieves all instances of the model.

        Args:
            session: The active SQLAlchemy async session.

        Returns:
            A list of all model instances.
        """
        from sqlalchemy.future import select
        try:
            result = await session.execute(select(self.model))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}", exc_info=True)
            raise
            
    async def find(self, session, **filters) -> list[ModelType]:
        """
        Finds entities that match the given filters.
        Args:
            session: The active SQLAlchemy session.
            **filters: Keyword arguments for filtering.
        Returns:
            A list of matching SQLAlchemy model instances.
        """
        from sqlalchemy.future import select
        try:
            query = select(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
                else:
                    logger.warning(f"Field {field} does not exist in {self.model.__name__}")
                    raise Exception(f"Field {field} does not exist in {self.model.__name__}")
            result = await session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding {self.model.__name__} by filters {filters}: {e}", exc_info=True)
            raise


    async def update(self, session, *, obj_in: ModelType) -> Optional[ModelType]:
        """
        Updates an existing model instance in the database.
        It uses merge to handle both attached and detached objects.

        Args:
            session: The active SQLAlchemy async session.
            obj_in: The model instance with updated data.

        Returns:
            The updated model instance or None on failure.
        """
        try:
            # Merge updates the object state and re-attaches it to the session.
            updated_obj = await session.merge(obj_in)
            await session.commit()
            await session.refresh(obj_in)
            return updated_obj
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}", exc_info=True)
            raise

    async def delete(self, session, *, entity_id: int) -> bool:
        """
        Deletes a model instance by its primary key.

        Args:
            session: The active SQLAlchemy async session.
            entity_id: The primary key of the entity to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        try:
            obj = await self.get_by_id(session, entity_id=entity_id)
            if obj:
                await session.delete(obj)
                await session.commit()
                return True
            return False
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {entity_id}: {e}", exc_info=True)
            raise

class RepositoryManager:
    """
    Manages the lifecycle and access to all repositories in the application.
    It ensures that for each SQLAlchemy model, a single repository instance is
    created and reused.
    """
    def __init__(self):
        self._repositories: Dict[Type[ModelType], GenericRepository] = {}
        logger.info("RepositoryManager initialized.")

    def register(self, model_class: Type[ModelType]):
        """
        Creates and registers a GenericRepository for a given SQLAlchemy model.
        If a repository for this model already exists, it does nothing.

        Args:
            model_class: The SQLAlchemy model class to be managed.
        """
        if model_class not in self._repositories:
            self._repositories[model_class] = GenericRepository(model=model_class)
            logger.info(f"Registered repository for model: {model_class.__name__}")

    def get(self, model_class: Type[ModelType]) -> GenericRepository:
        """
        Retrieves the repository instance for a specific model.

        Args:
            model_class: The SQLAlchemy model class.

        Returns:
            An instance of GenericRepository for the given model.

        Raises:
            KeyError: If no repository has been registered for the model class.
        """
        if model_class not in self._repositories:
            raise KeyError(f"No repository registered for model {model_class.__name__}. "
                           "Ensure it is registered in DatabaseManager.")
        return self._repositories[model_class]