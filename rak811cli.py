#!/usr/bin/env python3

import argparse
import serial
from tlwpy.rak811 import Rak811
from tlwpy.rak811 import Band
import asyncio
import logging
import re

from prompt_toolkit import PromptSession
import prompt_toolkit.eventloop
import prompt_toolkit.patch_stdout
import prompt_toolkit.lexers
import prompt_toolkit.completion
from prompt_toolkit import print_formatted_text, HTML
import dataparameter


class State:
    __slots__ = ['joined']

    def __init__(self):
        self.joined = False


class Parameter:
    __slots__ = ['name', 'value_description']

    def __init__(self, name: str, value_description='_value_'):
        self.name = name
        self.value_description = value_description


parameter_app_eui = Parameter('app_eui')
parameter_dev_eui = Parameter('dev_eui')
parameter_key = Parameter('key')
parameter_port = Parameter('port', value_description='1-223')
parameter_data = Parameter('data')
parameter_confirm = Parameter('confirm', value_description='(0|1)')

parameters = [
    parameter_app_eui,
    parameter_dev_eui,
    parameter_key,
    parameter_port,
    parameter_data,
    parameter_confirm
]


class Command:
    __slots__ = ['required_parameters', 'optional_parameters', 'possible_parameters']

    def __init__(self, required_parameters: [Parameter] = [], optional_parameters: [Parameter] = []):
        self.required_parameters = required_parameters
        self.optional_parameters = optional_parameters

        self.possible_parameters = []

        def param_name(p):
            return p.name

        self.possible_parameters += map(param_name, required_parameters)
        self.possible_parameters += map(param_name, optional_parameters)

    async def run(self, rak811, state: State, parameters: dict):
        pass


class HelpCommand(Command):
    async def run(self, rak811, required_parameters: dict):
        for command in commands:
            required_parameters = ' '.join(
                map(lambda p: '%s %s' % (p.name, p.value_description), commands[command].required_parameters))
            optional_parameters = ' '.join(
                map(lambda p: '[%s %s]' % (p.name, p.value_description), commands[command].optional_parameters))
            print_formatted_text(
                HTML('<b>%s</b> %s' % (command, ' '.join([required_parameters, optional_parameters]).strip())))


class JoinCommand(Command):
    def __init__(self):
        super(JoinCommand, self).__init__(optional_parameters=[parameter_app_eui, parameter_dev_eui, parameter_key])

    async def run(self, rak811, state: State, parameters: dict):
        if len(parameters) is 3:
            rak811.set_otaa_parameters(parameters['app_eui'], parameters['dev_eui'], parameters['key'])
        elif len(parameters) is not 0:
            print_formatted_text('either supply the app_eui, dev_eui and key or nothing')
            return
        rak811.join()
        state.joined = True


class SendCommand(Command):
    def __init__(self):
        super(SendCommand, self).__init__(required_parameters=[parameter_port, parameter_data],
                                          optional_parameters=[parameter_confirm])

    async def run(self, rak811, state: State, parameters: dict):
        if not state.joined:
            print_formatted_text(HTML('<b>join</b> first'))
            return

        port = int(parameters['port'])

        data = dataparameter.parse(parameters['data'])
        if data is None:
            print_formatted_text('couldnt parse data')
            return

        confirm = False
        if 'confirm' in parameters:
            confirm = bool(parameters['confirm'])

        rak811.send(port, data, confirmed=confirm)


commands = {
    'help': HelpCommand(),
    'join': JoinCommand(),
    'send': SendCommand()
}

pattern_field = '\\w{1,}'
field_patterns = [pattern_field, dataparameter.pattern_string, dataparameter.pattern_file,
                  dataparameter.pattern_file_quoted, dataparameter.pattern_b64]
parameter_regex = '(%s)\\s(%s)\\s?' % ('|'.join(map(lambda p: p.name, parameters)), '|'.join(field_patterns))
regex = '(%s)(\\s(%s){0,})?' % ('|'.join(commands), parameter_regex)


async def main(serialport: str):
    print(parameter_regex)

    logging.basicConfig(level=logging.DEBUG)

    state = State()

    rak811 = Rak811.from_path(serialport)
    rak811.reset()

    session = PromptSession()

    while True:
        with prompt_toolkit.patch_stdout.patch_stdout():
            result = await session.prompt('rak811> ', async_=True)
            match = re.fullmatch(regex, result)
            if match is not None:
                c = match.group(1)
                p = match.group(2)

                command = commands[c]

                call = True

                params = {}
                if p is not None:
                    for param in re.finditer(parameter_regex, p):
                        params[param.group(1)] = param.group(2)

                    invalid_params = list(filter(lambda pp: pp not in command.possible_parameters, params))
                    for invalid_param in invalid_params:
                        print_formatted_text(HTML('<b>%s</b> is not applicable to <b>%s</b>' % (invalid_param, c)))
                    call = len(invalid_params) == 0

                if call:
                    await command.run(rak811, state, params)

            else:
                print('dunno')

    ser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serialport', type=str, required=True)
    args = parser.parse_args()

    prompt_toolkit.eventloop.use_asyncio_event_loop()

    try:
        asyncio.get_event_loop().run_until_complete(main(args.serialport))
    except KeyboardInterrupt:
        print('dying..')
