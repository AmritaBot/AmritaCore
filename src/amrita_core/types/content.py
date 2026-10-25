from __future__ import annotations

import typing
from abc import ABC
from collections.abc import Sequence
from typing import Generic, Literal

from pydantic import Field, model_validator

from amrita_core.types.base import BaseModel

StringSub_T = typing.TypeVar("StringSub_T", bound=str)


class ImageUrl(BaseModel):
    url: str = Field(..., description="Image URL")
    detail: Literal["high", "low", "auto"] | None = Field(
        default=None,
        description="Image detail level",
        exclude_if=lambda x: x is None,
    )


class Content(
    ABC,
    BaseModel,
    Generic[StringSub_T],
    extra="allow",
):
    type: StringSub_T


class ImageContent(Content[Literal["image_url"]]):
    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl = Field(..., description="Image URL")


class TextContent(Content[Literal["text"]]):
    type: Literal["text"] = "text"
    text: str = Field(..., description="Text content")


class File(BaseModel):
    file_id: str | None = Field(
        default=None, description="File ID", exclude_if=lambda x: x is None
    )
    filename: str | None = Field(
        default=None, description="File name", exclude_if=lambda x: x is None
    )
    file_data: str | None = Field(
        default=None, description="File data", exclude_if=lambda x: x is None
    )
    type: str | None = Field(
        default=None, description="File type", exclude_if=lambda x: x is None
    )

    @model_validator(mode="after")
    def validate_file(self):
        has_id = self.file_id is not None
        has_inline = all([self.filename, self.file_data, self.type])

        if has_id and has_inline:
            raise ValueError("File id should be used alone")
        if not has_id and not has_inline:
            raise ValueError(
                "Either file_id or filename+file_data+type must be provided"
            )
        return self


class FileContent(Content[Literal["file"]]):
    type: Literal["file"] = "file"
    file: File = Field(..., description="File content")


CT_MAP: dict[str, type[Content]] = {}


def register_content(cls: type[Content]):
    """Register a Content subclass to CT_MAP based on its type field."""
    for field_name, field_info in cls.model_fields.items():
        if field_name == "type":
            type_value = None

            # Check if the field has a default value
            if not field_info.is_required():
                if field_info.default is not None:
                    type_value = field_info.default
                elif field_info.default_factory is not None:
                    type_value = field_info.default_factory()  # pyright: ignore[reportCallIssue]
            if type_value is None:
                annotation = field_info.annotation
                assert annotation is not None
                if (
                    hasattr(annotation, "__origin__")
                    and annotation.__origin__ is Literal
                ):
                    # Get the literal value(s) from the annotation
                    literal_args = annotation.__args__
                    if literal_args:
                        type_value = literal_args[0]  # Take the first literal value
                    else:
                        raise TypeError(
                            f"Cannot determine type value for {cls.__name__}"
                        )
                else:
                    raise ValueError(
                        f"Type field in {cls.__name__} must be a Literal type"
                    )

            # Register to CT_MAP
            CT_MAP[str(type_value)] = cls
            break


USER_INPUT = Sequence[Content] | str | None


def coerce_content(value: object) -> object:
    """把原始 ``content`` 载荷里的 dict 项转成已注册的 ``Content`` 模型。

    ``Message`` 与 ``ToolResult`` 共用这一份逻辑：两处各写一遍的话，以后新增
    ``Content`` 子类时总有一边会漏掉。
    """
    if not isinstance(value, list):
        return value
    validated: list[object] = []
    for item in value:
        if isinstance(item, dict):
            if "type" not in item:
                raise ValueError("Content item is missing 'type' field")
            content_type = item["type"]
            if content_type not in CT_MAP:
                raise ValueError(
                    f"Unknown content type: `{content_type}`, please register it by calling `register_content` first."
                )
            validated.append(CT_MAP[content_type].model_validate(item))
        else:
            validated.append(item)
    return validated
