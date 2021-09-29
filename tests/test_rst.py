"""Tests for the [RST-style parser][griffe.docstrings.rst]."""

from __future__ import annotations

import inspect

import pytest

from griffe.dataclasses import Argument, Arguments, Class, Data, Docstring, Function, Module
from griffe.docstrings import rst as parser
from griffe.docstrings.dataclasses import (
    DocstringArgument,
    DocstringAttribute,
    DocstringElement,
    DocstringException,
    DocstringReturn,
    DocstringSectionKind,
)

SOME_NAME = "foo"
SOME_TEXT = "descriptive test text"
SOME_EXTRA_TEXT = "more test text"
SOME_EXCEPTION_NAME = "SomeException"
SOME_OTHER_EXCEPTION_NAME = "SomeOtherException"


def parse(docstring: str, parent: Module | Class | Function | Data | None = None, **parser_opts):
    """Parse a doctring.

    Arguments:
        docstring: The docstring to parse.
        parent: The docstring's parent object.
        **parser_opts: Additional options accepted by the parser.

    Returns:
        The parsed sections, and warnings.
    """
    docstring_object = Docstring(docstring, lineno=1, endlineno=None)
    docstring_object.endlineno = len(docstring_object.lines) + 1
    if parent:
        docstring_object.parent = parent
        parent.docstring = docstring_object
    warnings = []
    parser.warn = lambda _docstring, _offset, message: warnings.append(message)
    sections = parser.parse(docstring_object, **parser_opts)
    return sections, warnings


def assert_argument_equal(actual: DocstringArgument, expected: DocstringArgument) -> None:
    """Help assert docstring arguments are equal.

    Arguments:
        actual: The actual argument.
        expected: The expected argument.
    """
    assert actual.name == expected.name
    assert_element_equal(actual, expected)
    assert actual.value == expected.value


def assert_attribute_equal(actual: DocstringAttribute, expected: DocstringAttribute) -> None:
    """Help assert docstring attributes are equal.

    Arguments:
        actual: The actual attribute.
        expected: The expected attribute.
    """
    assert actual.name == expected.name
    assert_element_equal(actual, expected)


def assert_element_equal(actual: DocstringElement, expected: DocstringElement) -> None:
    """Help assert docstring elements are equal.

    Arguments:
        actual: The actual element.
        expected: The expected element.
    """
    assert actual.annotation == expected.annotation
    assert actual.description == expected.description


@pytest.mark.parametrize(
    "docstring",
    [
        "One line docstring description",
        """
        Multiple line docstring description.

        With more text.
        """,
    ],
)
def test_parse__description_only_docstring__single_markdown_section(docstring):
    """Parse a single or multiline docstring.

    Arguments:
        docstring: A parametrized docstring.
    """
    sections, warnings = parse(docstring)

    assert len(sections) == 1
    assert sections[0].kind is DocstringSectionKind.text
    assert sections[0].value == inspect.cleandoc(docstring)
    assert not warnings


def test_parse__no_description__single_markdown_section():
    """Parse an empty docstring."""
    sections, warnings = parse("")

    assert len(sections) == 1
    assert sections[0].kind is DocstringSectionKind.text
    assert sections[0].value == ""
    assert not warnings


def test_parse__multiple_blank_lines_before_description__single_markdown_section():
    """Parse a docstring with initial blank lines."""
    sections, warnings = parse(
        """


        Now text"""
    )

    assert len(sections) == 1
    assert sections[0].kind is DocstringSectionKind.text
    assert sections[0].value == "Now text"
    assert not warnings


def test_parse__param_field__param_section():
    """Parse a parameter section."""
    sections, _ = parse(
        f"""
        Docstring with one line param.

        :param {SOME_NAME}: {SOME_TEXT}
        """
    )
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(sections[1].value[0], DocstringArgument(SOME_NAME, annotation=None, description=SOME_TEXT))


def test_parse__only_param_field__empty_markdown():
    """Parse only a parameter section."""
    sections, _ = parse(":param foo: text")
    assert len(sections) == 2
    assert sections[0].kind is DocstringSectionKind.text
    assert sections[0].value == ""


@pytest.mark.parametrize(
    "param_directive_name",
    [
        "param",
        "parameter",
        "arg",
        "argument",
        "key",
        "keyword",
    ],
)
def test_parse__all_param_names__param_section(param_directive_name):
    """Parse all parameters directives.

    Arguments:
        param_directive_name: A parametrized directive name.
    """
    sections, _ = parse(
        f"""
        Docstring with one line param.

        :{param_directive_name} {SOME_NAME}: {SOME_TEXT}
        """
    )
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(sections[1].value[0], DocstringArgument(SOME_NAME, annotation=None, description=SOME_TEXT))


@pytest.mark.parametrize(
    "docstring",
    [
        f"""
        Docstring with param with continuation, no indent.

        :param {SOME_NAME}: {SOME_TEXT}
        {SOME_EXTRA_TEXT}
        """,
        f"""
        Docstring with param with continuation, with indent.

        :param {SOME_NAME}: {SOME_TEXT}
          {SOME_EXTRA_TEXT}
        """,
    ],
)
def test_parse__param_field_multi_line__param_section(docstring):
    """Parse multiline directives.

    Arguments:
        docstring: A parametrized docstring.
    """
    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation=None, description=f"{SOME_TEXT} {SOME_EXTRA_TEXT}"),
    )


def test_parse__param_field_for_function__param_section_with_kind():
    """Parse parameters."""
    docstring = f"""
        Docstring with line continuation.

        :param foo: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation=None, description=SOME_TEXT),
    )


def test_parse__param_field_docs_type__param_section_with_type():
    """Parse parameters with types."""
    docstring = f"""
        Docstring with line continuation.

        :param str foo: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation="str", description=SOME_TEXT),
    )


def test_parse__param_field_type_field__param_section_with_type():
    """Parse parameters with separated types."""
    docstring = f"""
        Docstring with line continuation.

        :param foo: {SOME_TEXT}
        :type foo: str
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation="str", description=SOME_TEXT),
    )


def test_parse__param_field_type_field_first__param_section_with_type():
    """Parse parameters with separated types first."""
    docstring = f"""
        Docstring with line continuation.

        :type foo: str
        :param foo: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation="str", description=SOME_TEXT),
    )


@pytest.mark.parametrize("union", ["str or None", "None or str", "str or int", "str or int or float"])
def test_parse__param_field_type_field_or_none__param_section_with_optional(union):
    """Parse parameters with separated union types.

    Arguments:
        union: A parametrized union type.
    """
    docstring = f"""
        Docstring with line continuation.

        :param foo: {SOME_TEXT}
        :type foo: {union}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation=union.replace(" or ", " | "), description=SOME_TEXT),
    )


def test_parse__param_field_annotate_type__param_section_with_type():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param foo: {SOME_TEXT}
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation="str", kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    sections, warnings = parse(docstring, parent=function)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument(SOME_NAME, annotation="str", description=SOME_TEXT),
    )
    assert not warnings


def test_parse__param_field_no_matching_param__result_from_docstring():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param other: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument("other", annotation=None, description=SOME_TEXT),
    )


def test_parse__param_field_with_default__result_from_docstring():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param foo: {SOME_TEXT}
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation=None, kind=None, default=repr("")))
    function = Function(name="func", arguments=arguments)
    sections, warnings = parse(docstring, parent=function)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.arguments
    assert_argument_equal(
        sections[1].value[0],
        DocstringArgument("foo", annotation=None, description=SOME_TEXT, value=repr("")),
    )
    assert not warnings


def test_parse__param_field_no_matching_param__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param other: {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "No matching parameter for 'other'" in warnings[0]


def test_parse__invalid_param_field_only_initial_marker__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param foo {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to get ':directive: value' pair" in warnings[0]


def test_parse__invalid_param_field_wrong_part_count__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param: {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to parse field directive" in warnings[0]


def test_parse__param_twice__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param foo: {SOME_TEXT}
        :param foo: {SOME_TEXT} again
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation=None, kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    _, warnings = parse(docstring, parent=function)
    assert "Duplicate parameter entry for 'foo'" in warnings[0]


def test_parse__param_type_twice_doc__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param str foo: {SOME_TEXT}
        :type foo: str
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation=None, kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    _, warnings = parse(docstring, parent=function)
    assert "Duplicate parameter information for 'foo'" in warnings[0]


def test_parse__param_type_twice_type_directive_first__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :type foo: str
        :param str foo: {SOME_TEXT}
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation=None, kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    _, warnings = parse(docstring, parent=function)
    assert "Duplicate parameter information for 'foo'" in warnings[0]


def test_parse__param_type_twice_annotated__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param str foo: {SOME_TEXT}
        :type foo: str
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation="str", kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    _, warnings = parse(docstring, parent=function)
    assert "Duplicate parameter information for 'foo'" in warnings[0]


def test_parse__param_type_no_type__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param str foo: {SOME_TEXT}
        :type str
    """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation="str", kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    _, warnings = parse(docstring, parent=function)
    assert "Failed to get ':directive: value' pair from" in warnings[0]


def test_parse__param_type_no_name__error_message():
    """Parse a simple docstring."""
    docstring = f"""
        Docstring with line continuation.

        :param str foo: {SOME_TEXT}
        :type: str
        """

    arguments = Arguments()
    arguments.add(Argument("foo", annotation="str", kind=None, default=None))
    function = Function(name="func", arguments=arguments)
    _, warnings = parse(docstring, parent=function)
    assert "Failed to get parameter name from" in warnings[0]


@pytest.mark.parametrize(
    "docstring",
    [
        f"""
        Docstring with param with continuation, no indent.

        :var {SOME_NAME}: {SOME_TEXT}
        {SOME_EXTRA_TEXT}
        """,
        f"""
        Docstring with param with continuation, with indent.

        :var {SOME_NAME}: {SOME_TEXT}
          {SOME_EXTRA_TEXT}
        """,
    ],
)
def test_parse__attribute_field_multi_line__param_section(docstring):
    """Parse multiline attributes.

    Arguments:
        docstring: A parametrized docstring.
    """
    sections, warnings = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.attributes
    assert_attribute_equal(
        sections[1].value[0],
        DocstringAttribute(SOME_NAME, annotation=None, description=f"{SOME_TEXT} {SOME_EXTRA_TEXT}"),
    )
    assert not warnings


@pytest.mark.parametrize(
    "attribute_directive_name",
    [
        "var",
        "ivar",
        "cvar",
    ],
)
def test_parse__all_attribute_names__param_section(attribute_directive_name):
    """Parse all attributes directives.

    Arguments:
        attribute_directive_name: A parametrized directive name.
    """
    sections, warnings = parse(
        f"""
        Docstring with one line attribute.

        :{attribute_directive_name} {SOME_NAME}: {SOME_TEXT}
        """
    )
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.attributes
    assert_attribute_equal(
        sections[1].value[0],
        DocstringAttribute(SOME_NAME, annotation=None, description=SOME_TEXT),
    )
    assert not warnings


def test_parse__class_attributes__attributes_section():
    """Parse class attributes."""
    docstring = f"""
        Class docstring with attributes

        :var foo: {SOME_TEXT}
    """

    sections, _ = parse(docstring, parent=Class(name="klass"))
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.attributes
    assert_attribute_equal(
        sections[1].value[0],
        DocstringAttribute(SOME_NAME, annotation=None, description=SOME_TEXT),
    )


def test_parse__class_attributes_with_type__annotation_in_attributes_section():
    """Parse typed class attributes."""
    docstring = f"""
        Class docstring with attributes

        :vartype foo: str
        :var foo: {SOME_TEXT}
    """

    sections, _ = parse(docstring, parent=Class(name="klass"))
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.attributes
    assert_attribute_equal(
        sections[1].value[0],
        DocstringAttribute(SOME_NAME, annotation="str", description=SOME_TEXT),
    )


def test_parse__attribute_invalid_directive___error():
    """Warn on invalid attribute directive."""
    docstring = f"""
        Class docstring with attributes

        :var {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to get ':directive: value' pair from" in warnings[0]


def test_parse__attribute_no_name__error():
    """Warn on invalid attribute directive."""
    docstring = f"""
        Class docstring with attributes

        :var: {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to parse field directive from" in warnings[0]


def test_parse__attribute_duplicate__error():
    """Warn on duplicate attribute directive."""
    docstring = f"""
        Class docstring with attributes

        :var foo: {SOME_TEXT}
        :var foo: {SOME_TEXT}
        """

    _, warnings = parse(docstring)
    assert "Duplicate attribute entry for 'foo'" in warnings[0]


def test_parse__class_attributes_type_invalid__error():
    """Warn on invalid attribute type directive."""
    docstring = f"""
        Class docstring with attributes

        :vartype str
        :var foo: {SOME_TEXT}
        """

    _, warnings = parse(docstring)
    assert "Failed to get ':directive: value' pair from " in warnings[0]


def test_parse__class_attributes_type_no_name__error():
    """Warn on invalid attribute directive."""
    docstring = f"""
        Class docstring with attributes

        :vartype: str
        :var foo: {SOME_TEXT}
        """

    _, warnings = parse(docstring)
    assert "Failed to get attribute name from" in warnings[0]


def test_parse__return_directive__return_section_no_type():
    """Parse return directives."""
    docstring = f"""
        Function with only return directive

        :return: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.returns
    assert_element_equal(
        sections[1].value,
        DocstringReturn(annotation=None, description=SOME_TEXT),
    )


def test_parse__return_directive_rtype__return_section_with_type():
    """Parse typed return directives."""
    docstring = f"""
        Function with only return & rtype directive

        :return: {SOME_TEXT}
        :rtype: str
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.returns
    assert_element_equal(
        sections[1].value,
        DocstringReturn(annotation="str", description=SOME_TEXT),
    )


def test_parse__return_directive_rtype_first__return_section_with_type():
    """Parse typed-first return directives."""
    docstring = f"""
        Function with only return & rtype directive

        :rtype: str
        :return: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.returns
    assert_element_equal(
        sections[1].value,
        DocstringReturn(annotation="str", description=SOME_TEXT),
    )


def test_parse__return_directive_annotation__return_section_with_type():
    """Parse return directives with return annotation."""
    docstring = f"""
        Function with return directive, rtype directive, & annotation

        :return: {SOME_TEXT}
    """

    function = Function(name="func", returns="str")
    sections, _ = parse(docstring, parent=function)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.returns
    assert_element_equal(
        sections[1].value,
        DocstringReturn(annotation="str", description=SOME_TEXT),
    )


def test_parse__return_directive_annotation__prefer_return_directive():
    """Prefer docstring type over return annotation."""
    docstring = f"""
        Function with return directive, rtype directive, & annotation

        :return: {SOME_TEXT}
        :rtype: str
    """

    function = Function(name="func", returns="int")
    sections, _ = parse(docstring, parent=function)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.returns
    assert_element_equal(
        sections[1].value,
        DocstringReturn(annotation="str", description=SOME_TEXT),
    )


def test_parse__return_invalid__error():
    """Warn on invalid return directive."""
    docstring = f"""
        Function with only return directive

        :return {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to get ':directive: value' pair from " in warnings[0]


def test_parse__rtype_invalid__error():
    """Warn on invalid typed return directive."""
    docstring = """
        Function with only return directive

        :rtype str
    """

    _, warnings = parse(docstring)
    assert "Failed to get ':directive: value' pair from " in warnings[0]


def test_parse__raises_directive__exception_section():
    """Parse raise directives."""
    docstring = f"""
        Function with only return directive

        :raise SomeException: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.raises
    assert_element_equal(
        sections[1].value[0],
        DocstringException(annotation=SOME_EXCEPTION_NAME, description=SOME_TEXT),
    )


def test_parse__multiple_raises_directive__exception_section_with_two():
    """Parse multiple raise directives."""
    docstring = f"""
        Function with only return directive

        :raise SomeException: {SOME_TEXT}
        :raise SomeOtherException: {SOME_TEXT}
    """

    sections, _ = parse(docstring)
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.raises
    assert_element_equal(
        sections[1].value[0],
        DocstringException(annotation=SOME_EXCEPTION_NAME, description=SOME_TEXT),
    )
    assert_element_equal(
        sections[1].value[1],
        DocstringException(annotation=SOME_OTHER_EXCEPTION_NAME, description=SOME_TEXT),
    )


@pytest.mark.parametrize(
    "raise_directive_name",
    [
        "raises",
        "raise",
        "except",
        "exception",
    ],
)
def test_parse__all_exception_names__param_section(raise_directive_name):
    """Parse all raise directives.

    Arguments:
        raise_directive_name: A parametrized directive name.
    """
    sections, _ = parse(
        f"""
        Docstring with one line attribute.

        :{raise_directive_name} {SOME_EXCEPTION_NAME}: {SOME_TEXT}
        """
    )
    assert len(sections) == 2
    assert sections[1].kind is DocstringSectionKind.raises
    assert_element_equal(
        sections[1].value[0],
        DocstringException(annotation=SOME_EXCEPTION_NAME, description=SOME_TEXT),
    )


def test_parse__raise_invalid__error():
    """Warn on invalid raise directives."""
    docstring = f"""
        Function with only return directive

        :raise {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to get ':directive: value' pair from " in warnings[0]


def test_parse__raise_no_name__error():
    """Warn on invalid raise directives."""
    docstring = f"""
        Function with only return directive

        :raise: {SOME_TEXT}
    """

    _, warnings = parse(docstring)
    assert "Failed to parse exception directive from" in warnings[0]


# TODO: uncomment once Data is used
# def test_parse_module_attributes_section__expected_attributes_section():
#     """Parse attributes section in modules."""
#     docstring = """
#         Let's describe some attributes.

#         :var A: Alpha.
#         :var B: Beta.
#         :vartype B: bytes
#         :var C: Gamma.
#         :var D: Delta.
#         :var E: Epsilon.
#         :vartype E: float
#     """

#     module = Module(name="mod", filepath=None)
#     module["A"] = Data("A")  # annotation="int", value="0"
#     module["B"] = Data("B")  # annotation="str", value=repr("ŧ")
#     module["C"] = Data("C")  # annotation="bool", value="True"
#     module["D"] = Data("D")  # annotation=None, value="3.0"
#     module["E"] = Data("E")  # annotation=None, value="None"
#     sections, warnings = parse(docstring)

#     attr_section = sections[1]
#     assert attr_section.kind is DocstringSectionKind.attributes
#     assert len(attr_section.value) == 5
#     expected_kwargs = [
#         {"name": "A", "annotation": "int", "description": "Alpha."},
#         {"name": "B", "annotation": "bytes", "description": "Beta."},
#         {"name": "C", "annotation": "bool", "description": "Gamma."},
#         {"name": "D", "annotation": None, "description": "Delta."},
#         {"name": "E", "annotation": "float", "description": "Epsilon."},
#     ]
#     for index, expected in enumerate(expected_kwargs):
#         assert_annotated_obj_equal(attr_section.value[index], DocstringAttribute(**expected))
#     assert not warnings
