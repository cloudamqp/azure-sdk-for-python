# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import logging
import warnings
from os import PathLike
from typing import IO, AnyStr, Type, Union

from marshmallow import ValidationError

from azure.ai.ml._ml_exceptions import ErrorCategory, ErrorTarget, ValidationErrorType, ValidationException
from azure.ai.ml._utils.utils import load_yaml
from azure.ai.ml.entities._assets._artifacts.code import Code
from azure.ai.ml.entities._assets._artifacts.data import Data
from azure.ai.ml.entities._assets._artifacts.model import Model
from azure.ai.ml.entities._assets.environment import Environment
from azure.ai.ml.entities._component.command_component import CommandComponent
from azure.ai.ml.entities._component.component import Component
from azure.ai.ml.entities._component.parallel_component import ParallelComponent
from azure.ai.ml.entities._component.pipeline_component import PipelineComponent
from azure.ai.ml.entities._compute.compute import Compute
from azure.ai.ml.entities._datastore.datastore import Datastore
from azure.ai.ml.entities._deployment.batch_deployment import BatchDeployment
from azure.ai.ml.entities._deployment.online_deployment import OnlineDeployment
from azure.ai.ml.entities._endpoint.batch_endpoint import BatchEndpoint
from azure.ai.ml.entities._endpoint.online_endpoint import OnlineEndpoint
from azure.ai.ml.entities._job.job import Job
from azure.ai.ml.entities._registry.registry import Registry
from azure.ai.ml.entities._resource import Resource
from azure.ai.ml.entities._schedule.schedule import JobSchedule
from azure.ai.ml.entities._validation import SchemaValidatableMixin, _ValidationResultBuilder
from azure.ai.ml.entities._workspace.connections.workspace_connection import WorkspaceConnection
from azure.ai.ml.entities._workspace.workspace import Workspace

module_logger = logging.getLogger(__name__)

_DEFAULT_RELATIVE_ORIGIN = "./"


def load_common(
    cls: Type[Resource],
    source: Union[str, PathLike, IO[AnyStr]],
    path: Union[str, PathLike],
    relative_origin: str,
    args: tuple,
    params_override: list = None,
    **kwargs,
) -> Resource:
    """Private function to load a yaml file to an entity object.

    :param cls: The entity class type.
    :type cls: type[Resource]
    :param source: A source of yaml.
    :type source: Union[str, PathLike, IO[AnyStr]]
    :param path: Deprecated way to input a file path source.
        Maintained here to allow deprecated input parsing from users.
    :type path: Union[str, Pathlike]
    :param relative_origin: The origin of to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Must be provided, and is assumed to be assigned by other internal
        functions that call this.
    :type relative_origin: str
    :param args: *args input from caller functions. Kept as a potential deprecated input
        method for the path input.
    :type args: tuple
    :param params_override: _description_, defaults to None
    :type params_override: list, optional
    :return: _description_
    :rtype: Resource
    """

    # Check for deprecated path input, either named or as first unnamed input
    if source is None:
        if args is not None and len(args) > 0:
            source = args[0]
        elif path is not None:
            source = path
            warnings.warn(
                "the 'path' input for load functions is deprecated. Please use 'source' instead.", DeprecationWarning
            )

    if relative_origin is None:
        if isinstance(source, (str, PathLike)):
            relative_origin = source
        else:
            try:
                relative_origin = source.name
            except AttributeError:  # input is a stream or something
                relative_origin = _DEFAULT_RELATIVE_ORIGIN

    params_override = params_override or []
    yaml_dict = _try_load_yaml_dict(source)

    cls, type_str = cls._resolve_cls_and_type(data=yaml_dict, params_override=params_override)

    try:
        return _load_common_raising_marshmallow_error(cls, yaml_dict, relative_origin, params_override, **kwargs)
    except ValidationError as e:
        if issubclass(cls, SchemaValidatableMixin):
            validation_result = _ValidationResultBuilder.from_validation_error(e, relative_origin)
            validation_result.try_raise(
                error_target=cls._get_validation_error_target(),
                schema=cls._create_schema_for_validation_with_base_path(),
                raise_mashmallow_error=True,
                additional_message=""
                if type_str is None
                else f"If you are trying to configure an entity that is not "
                f"of type {type_str}, please specify the correct "
                f"type in the 'type' property.",
            )
        else:
            raise e


def _try_load_yaml_dict(source: Union[str, PathLike, IO[AnyStr]]) -> dict:
    yaml_dict = load_yaml(source)
    if yaml_dict is None:  # This happens when a YAML is empty.
        msg = "Target yaml file is empty"
        raise ValidationException(
            message=msg,
            target=ErrorTarget.COMPONENT,
            no_personal_data_message=msg,
            error_category=ErrorCategory.USER_ERROR,
            error_type=ValidationErrorType.CANNOT_PARSE,
        )
    if not isinstance(yaml_dict, dict):  # This happens when a YAML file is mal formatted.
        msg = "Expect dict but get {} after parsing yaml file"
        raise ValidationException(
            message=msg.format(type(yaml_dict)),
            target=ErrorTarget.COMPONENT,
            no_personal_data_message=msg.format(type(yaml_dict)),
            error_category=ErrorCategory.USER_ERROR,
            error_type=ValidationErrorType.CANNOT_PARSE,
        )
    return yaml_dict


def _load_common_raising_marshmallow_error(
    cls: Type[Resource], yaml_dict, relative_origin: Union[PathLike, str], params_override: list = None, **kwargs
) -> Resource:
    return cls._load(data=yaml_dict, yaml_path=relative_origin, params_override=params_override, **kwargs)


def load_job(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Job:
    """Construct a job object from a yaml file.

    :param source: The local yaml source of a job. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Loaded job object.
    :rtype: Job
    """
    return load_common(Job, source, path, relative_origin, args, **kwargs)


def load_workspace(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Workspace:
    """Load a workspace object from a yaml file.

    :param source: The local yaml source of a workspace. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Loaded workspace object.
    :rtype: Workspace
    """
    return load_common(Workspace, source, path, relative_origin, args, **kwargs)


def load_registry(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Registry:
    """Load a registry object from a yaml file.

    :param source: The local yaml source of a registry. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Loaded registry object.
    :rtype: Registry
    """
    return load_common(Registry, source, path, relative_origin, args, **kwargs)


def load_datastore(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Datastore:
    """Construct a datastore object from a yaml file.

    :param source: The local yaml source of a datastore. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Loaded datastore object.
    :rtype: Datastore
    """
    return load_common(Datastore, source, path, relative_origin, args, **kwargs)


def load_code(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Code:
    """Construct a code object from a yaml file.

    :param source: The local yaml source of a code object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Loaded compute object.
    :rtype: Compute
    """
    return load_common(Code, source, path, relative_origin, args, **kwargs)


def load_compute(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Compute:
    """Construct a compute object from a yaml file.

    :param source: The local yaml source of a compute. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Loaded compute object.
    :rtype: Compute
    """
    return load_common(Compute, source, path, relative_origin, args, **kwargs)


def load_component(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Union[CommandComponent, ParallelComponent, PipelineComponent]:
    """Load component from local or remote to a component function.

    For example:

    .. code-block:: python

        # Load a local component to a component function.
        component_func = load_component(source="custom_component/component_spec.yaml")
        # Load a remote component to a component function.
        component_func = load_component(client=ml_client, name="my_component", version=1)

        # Consuming the component func
        component = component_func(param1=xxx, param2=xxx)

    :param source: The local yaml source of a component. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param client: An MLClient instance.
    :type client: MLClient
    :param name: Name of the component.
    :type name: str
    :param version: Version of the component.
    :type version: str
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]
    :param kwargs: A dictionary of additional configuration parameters.
    :type kwargs: dict

    :return: A function that can be called with parameters to get a `azure.ai.ml.entities.Component`
    :rtype: Union[CommandComponent, ParallelComponent, PipelineComponent]
    """

    client = kwargs.pop("client", None)
    name = kwargs.pop("name", None)
    version = kwargs.pop("version", None)

    # Check for deprecated path input earlier than usual due to extra checks in this function.
    if source is None:
        if args is not None and len(args) > 0:
            source = args[0]
        elif path is not None:
            source = path
            warnings.warn(
                "the 'path' input for load functions is deprecated. Please use 'source' instead.", DeprecationWarning
            )

    if source:
        component_entity = load_common(Component, source, path, relative_origin, args, **kwargs)
    elif client and name and version:
        component_entity = client.components.get(name, version)
    else:
        msg = "One of (client, name, version), (source) should be provided."
        raise ValidationException(
            message=msg,
            no_personal_data_message=msg,
            target=ErrorTarget.COMPONENT,
            error_category=ErrorCategory.USER_ERROR,
            error_type=ValidationErrorType.MISSING_VALUE,
        )
    return component_entity


def load_model(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Model:
    """Construct a model object from yaml file.

    :param source: The local yaml source of a model. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed model object.
    :rtype: Model
    """
    return load_common(Model, source, path, relative_origin, args, **kwargs)


def load_data(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Data:
    """Construct a data object from yaml file.

    :param source: The local yaml source of a data object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed data object.
    :rtype: Data
    """
    return load_common(Data, source, path, relative_origin, args, **kwargs)


def load_environment(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> Environment:
    """Construct a environment object from yaml file.

    :param source: The local yaml source of an environment. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed environment object.
    :rtype: Environment
    """
    return load_common(Environment, source, path, relative_origin, args, **kwargs)


def load_online_deployment(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> OnlineDeployment:
    """Construct a online deployment object from yaml file.

    :param source: The local yaml source of an online deployment object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed online deployment object.
    :rtype: OnlineDeployment
    """
    return load_common(OnlineDeployment, source, path, relative_origin, args, **kwargs)


def load_batch_deployment(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> BatchDeployment:
    """Construct a batch deployment object from yaml file.

    :param source: The local yaml source of a batch deployment object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed batch deployment object.
    :rtype: BatchDeployment
    """
    return load_common(BatchDeployment, source, path, relative_origin, args, **kwargs)


def load_online_endpoint(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> OnlineEndpoint:
    """Construct a online endpoint object from yaml file.

    :param source: The local yaml source of an online endpoint object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed online endpoint object.
    :rtype: OnlineEndpoint
    """
    return load_common(OnlineEndpoint, source, path, relative_origin, args, **kwargs)


def load_batch_endpoint(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> BatchEndpoint:
    """Construct a batch endpoint object from yaml file.

    :param source: The local yaml source of a batch endpoint object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed batch endpoint object.
    :rtype: BatchEndpoint
    """
    return load_common(BatchEndpoint, source, path, relative_origin, args, **kwargs)


def load_workspace_connection(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> WorkspaceConnection:
    """Construct a workspace connection object from yaml file.

    :param source: The local yaml source of a workspace connection object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed workspace connection object.
    :rtype: WorkspaceConnection
    """
    return load_common(WorkspaceConnection, source, path, relative_origin, args, **kwargs)


def load_schedule(
    *args,
    source: Union[str, PathLike, IO[AnyStr]] = None,
    relative_origin: str = None,
    path: Union[str, PathLike] = None,
    **kwargs,
) -> JobSchedule:
    """Construct a schedule object from yaml file.

    :param source: The local yaml source of a schedule object. Must be either a
        path to a local file, or an already-open file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
        If the source is an open file, the file will be read directly,
        and an exception is raised if the file is not readable.
    :type source: Union[PathLike, str, io.TextIOWrapper]
    :param relative_origin: The origin to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Defaults to the inputted source's directory if it is a file or file path input.
        Defaults to "./" if the source is a stream input with no name value.
    :type relative_origin: str
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :param path: Deprecated path to a local file as the source. It's recommended
        that you change 'path=' inputs to 'source='. The first unnamed input of this function
        is also treated like a path input.
    :type path: Union[str, Pathlike]

    :return: Constructed schedule object.
    :rtype: JobSchedule
    """
    return load_common(JobSchedule, source, path, relative_origin, args, **kwargs)
