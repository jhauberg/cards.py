# coding=utf-8

from cards.constants import Columns

from cards.util import terminal_supports_color


class WarningContext:
    """ Represents the context of a warning. """

    def __init__(self, name: str, row_index: int=-1, card_index: int=-1, card_copy_index: int=-1):
        self.name = name
        self.row_index = row_index
        self.card_index = card_index
        self.card_copy_index = card_copy_index


def warn(message: str, in_context: WarningContext=None, as_error=False) -> None:
    """ Display a command-line warning, optionally showing its context. """

    apply_color = (WarningDisplay.apply_error_color if as_error
                   else WarningDisplay.apply_warning_color)

    message_context = '[{0}]'.format('!' if as_error else '-')

    if in_context is not None:
        if in_context.row_index > -1:
            if in_context.card_index > -1:
                if in_context.card_copy_index > -1:
                    message_context = '{0} [{1}:#{2}.{4}~{3}]'.format(
                        message_context, in_context.name,
                        in_context.row_index, in_context.card_index, in_context.card_copy_index)
                else:
                    message_context = '{0} [{1}:#{2}~{3}]'.format(
                        message_context, in_context.name,
                        in_context.row_index, in_context.card_index)
            else:
                message_context = '{0} [{1}:#{2}]'.format(
                    message_context, in_context.name, in_context.row_index)
        else:
            message_context = '{0} [{1}]'.format(
                message_context, in_context.name)

    message_content = message_context + ' ' + message

    print(apply_color + message_content + WarningDisplay.apply_normal_color)


class WarningDisplay:
    apply_error_color = '\033[31m' if terminal_supports_color() else ''
    apply_error_color_underlined = '\033[4;31m' if terminal_supports_color() else ''
    apply_warning_color = '\033[33m' if terminal_supports_color() else ''
    apply_warning_color_underlined = '\033[4;33m' if terminal_supports_color() else ''
    apply_normal_color = '\033[0m' if terminal_supports_color() else ''

    @staticmethod
    def ambiguous_reference(context: WarningContext,
                            reference: str,
                            result: str) -> None:
        truncated_result = (result if len(result) < 18 else result[:18] + '…')

        warn('A reference named \'{0}\' could refer to both a column or a definition. '
             'The column data \'{1}\' was used.'
             .format(reference, truncated_result),
             in_context=context)

    @staticmethod
    def unknown_size_specification(context: WarningContext,
                                   size_specification: str) -> None:
        warn('The size specification \'{0}\' has not been defined. '
             'Image might not display as expected.'
             .format(size_specification),
             in_context=context)

    @staticmethod
    def invalid_width_specification(context: WarningContext,
                                    width: int) -> None:
        warn('An image cannot have a width of \'{0}\'. '
             'Image will be shown at its intrinsic size.'
             .format(width),
             in_context=context)

    @staticmethod
    def invalid_height_specification(context: WarningContext,
                                     height: int) -> None:
        warn('An image cannot have a height of \'{0}\'. '
             'Image will be shown at its intrinsic size.'
             .format(height),
             in_context=context)

    @staticmethod
    def unresolved_image_reference_error(image_reference: str,
                                         closest_resolution_value: str) -> None:
        warn('An image reference could not be resolved: \'{0}\'. '
             'Was it supposed to be: \'{1}\'?'
             .format(image_reference, closest_resolution_value),
             as_error=True)

    @staticmethod
    def included_file_not_found_error(context: WarningContext,
                                      included_file_path: str) -> None:
        warn('An included file was not found: {0}\'{1}\''
             .format(WarningDisplay.apply_error_color_underlined, included_file_path),
             in_context=context,
             as_error=True)

    @staticmethod
    def preview_enabled() -> None:
        warn('Preview is enabled. Only 1 of each card will be rendered.')

    @staticmethod
    def image_not_copied(context: WarningContext,
                         image_path: str) -> None:
        warn('An image was not copied to the output directory since it was specified with '
             'an absolute path: {0}\'{1}\''
             .format(WarningDisplay.apply_warning_color_underlined, image_path),
             in_context=context)

    @staticmethod
    def missing_image_error(context: WarningContext,
                            image_path: str) -> None:
        warn('One or more cards contain an image reference that does not exist: {0}\'{1}\''
             .format(WarningDisplay.apply_error_color_underlined, image_path),
             in_context=context,
             as_error=True)

    @staticmethod
    def bad_definitions_file_error(definitions_path: str) -> None:
        warn('No definitions file was found at: {0}\'{1}\''
             .format(WarningDisplay.apply_error_color_underlined, definitions_path),
             as_error=True)

    @staticmethod
    def using_automatically_found_definitions(definitions_path: str) -> None:
        warn('No definitions have been specified. Using definitions automatically found at: '
             '{0}\'{1}\''
             .format(WarningDisplay.apply_warning_color_underlined, definitions_path))

    @staticmethod
    def assume_backs(context: WarningContext) -> None:
        warn('Assuming card backs should be generated since ' +
             '\'' + Columns.TEMPLATE_BACK + '\' appears in data. '
             'You can disable card backs by specifying the --disable-backs argument.',
             in_context=context)

    @staticmethod
    def no_backs(context: WarningContext) -> None:
        warn('Card backs will not be generated since \'' + Columns.TEMPLATE_BACK + '\''
             ' does not appear in data.',
             in_context=context)

    @staticmethod
    def indeterminable_count(context: WarningContext) -> None:
        warn('The card provided an indeterminable count and was skipped.',
             in_context=context)

    @staticmethod
    def missing_default_template(context: WarningContext) -> None:
        warn('A template was not provided and auto-templating is not enabled.'
             'Cards will not be generated correctly.',
             in_context=context)

    @staticmethod
    def missing_template_error(context: WarningContext) -> None:
        warn('The card did not provide a template.',
             in_context=context,
             as_error=True)

    @staticmethod
    def empty_template(context: WarningContext,
                       template_path: str,
                       is_back_template: bool=False) -> None:
        warning = ('The card provided a back template that appears to be empty: {0}\'{1}\'{2}.'
                   if is_back_template else
                   'The card provided a template that appears to be empty: {0}\'{1}\'{2}. '
                   'The card will use an auto-template instead, if possible.')

        warn(warning.format(WarningDisplay.apply_warning_color_underlined, template_path,
                            WarningDisplay.apply_warning_color),
             in_context=context)

    @staticmethod
    def using_auto_template(context: WarningContext) -> None:
        warn('The card did not provide a template. The card will use an auto-template instead.',
             in_context=context)

    @staticmethod
    def unknown_fields_in_template(context: WarningContext,
                                   unknown_fields: list,
                                   is_back_template: bool=False) -> None:
        if len(unknown_fields) > 1:
            warning = ('The back template contains fields that are not present for this card: {0}'
                       if is_back_template else
                       'The template contains fields that are not present for this card: {0}')
        else:
            unknown_fields = unknown_fields[0]

            warning = ('The back template contains a field that is not present for this card: \'{0}\''
                       if is_back_template else
                       'The template contains a field that is not present for this card: \'{0}\'')

        warn(warning.format(unknown_fields),
             in_context=context)

    @staticmethod
    def missing_fields_in_template(context: WarningContext,
                                   missing_fields: list,
                                   is_back_template: bool=False) -> None:
        if len(missing_fields) > 1:
            warning = ('The card back has unused columns: {0}'
                       if is_back_template else
                       'The card has unused columns: {0}')
        else:
            missing_fields = missing_fields[0]

            warning = ('The card back has an unused column: \'{0}\''
                       if is_back_template else
                       'The card has an unused column: \'{0}\'')

        warn(warning.format(missing_fields),
             in_context=context)

    @staticmethod
    def unused_definitions(unused_definitions: list) -> None:
        if len(unused_definitions) > 1:
            warning = 'You have definitions that seem to be unused: {0}'
        else:
            unused_definitions = unused_definitions[0]

            warning = 'You have a definition that seem to be unused: \'{0}\''

        warn(warning.format(unused_definitions))

    @staticmethod
    def invalid_columns_error(context: WarningContext,
                              invalid_columns: list) -> None:
        if len(invalid_columns) > 1:
            warning = 'Skipping datasource. Some column names are invalid: {0}'
        else:
            invalid_columns = invalid_columns[0]

            warning = 'Skipping datasource. A column name is invalid: {0}'

        warn(warning.format(invalid_columns),
             in_context=context,
             as_error=True)

    @staticmethod
    def bad_data_path_error(context: WarningContext,
                            data_path: str) -> None:
        warn('The datasource could not be found at: {0}\'{1}\''
             .format(WarningDisplay.apply_error_color_underlined, data_path),
             in_context=context,
             as_error=True)

    @staticmethod
    def bad_template_path_error(context: WarningContext,
                                template_path: str,
                                is_back: bool=False) -> None:
        warning = ('The card provided a back template that could not be opened: {0}\'{1}\''
                   if is_back else
                   'The card provided a template that could not be opened: {0}\'{1}\'')

        warn(warning.format(WarningDisplay.apply_error_color_underlined, template_path),
             in_context=context,
             as_error=True)

    @staticmethod
    def abort_unusually_high_count(context: WarningContext,
                                   count: int) -> bool:
        # arbitrarily determined amount- but if the count is really high
        # it might just be an error
        warn('The card has specified a high count: {0}. '
             'Are you sure you want to continue?'.format(count),
             in_context=context)

        answer = input('(Y)es or (n)o?').strip().lower()

        if answer == 'n' or answer == 'no':
            return True

        return False

    @staticmethod
    def bad_card_size(context: WarningContext,
                      size_identifier: str) -> None:
        warn('Cards will be default size because an unknown card size was specified: \'{0}\''
             .format(size_identifier),
             in_context=context)

    @staticmethod
    def card_was_skipped_intentionally(context: WarningContext) -> None:
        warn('The card was skipped.',
             in_context=context)
