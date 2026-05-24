# TextContent

The TextContent class represents text content within messages.

## Properties

- `type` (Literal["text"]): Content type, fixed as "text"
- `text` (str): Text content

## Description

The TextContent class inherits from the Content base class and is the concrete implementation for representing text content. In AmritaCore's messaging system, text content is one of the fundamental components of messages.

TextContent is one type of Content, along with ImageContent, forming the multimodal content support in the messaging system. This design enables the system to handle various types of content including text and images.
