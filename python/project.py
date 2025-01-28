import os

import packaging
from sipbuild import Option, Project, PyProjectOptionException


class FakeVimProject(Project):

    def _set_initial_configuration(self, pyproject, tool):
        print("Setting initial configuration", pyproject, tool)
        # Get the metadata and extract the version.
        self.metadata = pyproject.get_metadata()
        self._metadata_overrides = self.get_metadata_overrides()
        self.metadata.update(self._metadata_overrides)
        self.version_str = self.metadata['version']

        # Convert the version as a string to number.
        base_version = packaging.version.parse(self.version_str).base_version
        base_version = base_version.split('.')
        print('base_version', base_version)

        while len(base_version) < 3:
            base_version.append('0')

        version = 0
        for part in base_version:
            version <<= 8

            try:
                version += int(part)
            except ValueError:
                raise PyProjectOptionException('version',
                                               "'{0}' is an invalid version number".format(
                                                   self.version_str),
                                               section_name='tool.sip.metadata')

        self.version = version

        print('before configure', version)
        # Configure the project.
        self.configure(pyproject, 'tool.sip.project', tool)
        print('after configure', version)

        # Create and configure the builder.
        self.builder = self.builder_factory(self)
        self.builder.configure(pyproject, 'tool.sip.builder', tool)

        # For each set of bindings configuration make sure a bindings object
        # exists, creating it if necessary.
        bindings_sections = pyproject.get_section('tool.sip.bindings')
        if bindings_sections is not None:
            for name in bindings_sections.keys():
                if name not in self.bindings:
                    bindings = self.bindings_factory(self, name)
                    self.bindings[bindings.name] = bindings

        # Add a default set of bindings if none were defined.
        if not self.bindings:
            bindings = self.bindings_factory(self, self.metadata['name'])
            self.bindings[bindings.name] = bindings

        # Now configure each set of bindings.
        for bindings in self.bindings.values():
            bindings.configure(pyproject, 'tool.sip.bindings.' + bindings.name,
                               tool)

        # print('call super')
        # super()._set_initial_configuration(pyproject, tool)


    def configure(self, pyproject, section_name, tool):
        """ Perform the initial configuration of an object. """

        section = pyproject.get_section(section_name)

        if section is not None:
            for name, value in section.items():
                # Find the corresponding option.
                for option in self.get_options():
                    if option.user_name == name:
                        break
                else:
                    raise PyProjectOptionException(name,
                                                   "is not a supported option",
                                                   section_name=section_name)

                # Check the type of the option.
                print('hi!')
                if not isinstance(value, option.option_type):
                    print(name,
                                                   "should be of type '{0}' and not '{1}'".format(
                                                       option.option_type.__name__,
                                                       type(value).__name__))
                    raise PyProjectOptionException(name,
                                                   "should be of type '{0}' and not '{1}'".format(
                                                       option.option_type.__name__,
                                                       type(value).__name__),
                                                   section_name=section_name)

                # Check the option hasn't already been initialised.
                if getattr(self, option.name) is not None:
                    raise PyProjectOptionException(name,
                                                   "has already been set in code and cannot be "
                                                   "changed",
                                                   section_name=section_name)

                # Evaluate any environment markers if the option supports them.
                if isinstance(value, list):
                    new_value = []

                    for v in value:
                        v = self._handle_marker(v, name, section_name)
                        if v is not None:
                            new_value.append(v)

                    value = new_value

                setattr(self, option.name, value)

        self.apply_nonuser_defaults(tool)
