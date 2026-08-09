"""Exception module"""

MESSAGE_NOT_PROVIDER_INSTANCE = (
    "Problem validating the '{name}' object type; this is not an "
    "instance of codeloop.abc.Provider"
)


class NotProviderInstance(Exception):
    def __init__(self, name: str):
        super().__init__(MESSAGE_NOT_PROVIDER_INSTANCE.format(name=name))
