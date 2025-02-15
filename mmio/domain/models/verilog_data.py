from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, field_validator

from mmio.core.exceptions import ValidationError
from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class _MMIOTracker:
    """Internal tracker for MMIO data and statistics."""

    all_instances: list["VerilogData"] = []
    address_bit_widths: dict[str, int] = {}
    default_values: dict[int, tuple[str, str]] = {}

    @classmethod
    def add_instance(cls, instance: "VerilogData") -> None:
        """Add a VerilogData instance to tracking."""
        cls.all_instances.append(instance)

    @classmethod
    def update_address_bit_width(cls, address: str | None, value: str | None) -> None:
        """Update the maximum bit width needed for a given address."""
        if address is None or value is None:
            return

        current_width = VerilogData.calculate_bit_width(value)
        existing_width = cls.address_bit_widths.get(address, 0)
        cls.address_bit_widths[address] = max(current_width, existing_width)

    @classmethod
    def update_default_values(cls, bar: int | None, operation: str | None, value: str | None) -> None:
        """Update default values for a BAR based on new value."""
        if bar is None or operation is None or value is None:
            return

        if bar not in cls.default_values:
            cls.default_values[bar] = ("00000000", "00000000")

        current_defaults = cls.default_values[bar]
        if operation == "R":
            cls.default_values[bar] = (value, current_defaults[1])
        else:
            cls.default_values[bar] = (current_defaults[0], value)

    @classmethod
    def get_default_values(cls, bar: int) -> tuple[str, str]:
        """Get default read/write values for a BAR."""
        return cls.default_values.get(bar, ("00000000", "00000000"))

    @classmethod
    def get_bar_address_bit_widths(cls, bar: int) -> dict[str, int]:
        """Get all addresses and their bit widths for a specific BAR."""
        bar_addresses = set(VerilogData.addresses(bar=bar))
        return {addr: width for addr, width in cls.address_bit_widths.items() if addr in bar_addresses}


class VerilogData(BaseModel):
    """Data class for MMIO data."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    _tracker: ClassVar[_MMIOTracker] = _MMIOTracker()

    operation: str | None = None
    bar: int | None = None
    value: str | None = None
    address: str | None = None
    register_value: str | None = None
    timestamp: float | None = None
    description: str | None = None

    @classmethod
    def from_dict(cls, data_dict: dict[str, Any]) -> "VerilogData":
        """Create a VerilogData instance from a dictionary and update class tracking.

        Args:
            data_dict: Dictionary containing the MMIO data fields

        Returns:
            VerilogData instance with all class tracking updated

        Raises:
            ValidationError: If the data is invalid

        """
        try:
            if "bar" in data_dict and data_dict["bar"] is not None:
                data_dict["bar"] = int(data_dict["bar"])
            if "timestamp" in data_dict and data_dict["timestamp"] is not None:
                data_dict["timestamp"] = float(data_dict["timestamp"])

            for field in ["address", "register_value", "value"]:
                if field in data_dict and data_dict[field] is not None:
                    data_dict[field] = str(data_dict[field])

            instance = cls(
                operation=data_dict.get("operation"),
                bar=data_dict.get("bar"),
                value=data_dict.get("value"),
                address=data_dict.get("address"),
                register_value=data_dict.get("register_value"),
                timestamp=data_dict.get("timestamp"),
                description=data_dict.get("description"),
            )

            instance.format_and_validate()

            cls._tracker.add_instance(instance)

            if instance.address is not None and instance.value is not None:
                cls._tracker.update_address_bit_width(instance.address, instance.value)

            if instance.bar is not None and instance.operation is not None and instance.value is not None:
                cls._tracker.update_default_values(instance.bar, instance.operation, instance.value)

            return instance
        except Exception as e:
            logger.error(f"Error creating VerilogData from dict: {e}")
            raise ValidationError(f"Failed to create VerilogData: {str(e)}")

    def format_and_validate(self) -> None:
        """Format all values and validate them."""
        if self.value is not None:
            self.value = self.remove_0x(self.value, self.address)
        if self.register_value is not None:
            self.register_value = self.remove_0x(self.register_value, self.address)
        if self.address is not None:
            self.address = self.remove_0x(self.address, None)

        if self.address is not None:
            self.address = self.format_value(self.address, is_address=True)
        if self.value is not None:
            self.value = self.format_value(self.value, is_address=False)
        if self.register_value is not None:
            self.register_value = self.format_value(self.register_value, is_address=False)
        if self.timestamp is not None:
            self.timestamp = self.normalize_timestamp(self.timestamp)

        if self.bar is not None:
            self.bar = self.validate_bar(self.bar)
        if self.operation is not None:
            self.operation = self.validate_operation(self.operation)
        if self.address is not None:
            self.address = self.validate_address(self.address)
        if self.register_value is not None:
            self.register_value = self.validate_register_value(self.register_value)
        self.timestamp = self.validate_timestamp(self.timestamp)

    @classmethod
    def get_all_instances(cls) -> list["VerilogData"]:
        """Get all VerilogData instances."""
        return cls._tracker.all_instances

    @classmethod
    def get_address_bit_widths(cls) -> dict[str, int]:
        """Get all address bit widths."""
        return cls._tracker.address_bit_widths

    @classmethod
    def get_default_values(cls, bar: int) -> tuple[str, str]:
        """Get default read/write values for a BAR."""
        return cls._tracker.get_default_values(bar)

    @classmethod
    def get_bar_address_bit_widths(cls, bar: int) -> dict[str, int]:
        """Get all addresses and their bit widths for a specific BAR."""
        return cls._tracker.get_bar_address_bit_widths(bar)

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, value: str | None) -> str | None:
        """Validate the operation."""
        if value is None:
            return None
        if value not in ["R", "W"]:
            raise ValidationError(f"Invalid operation: {value}")
        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        """Validate the address."""
        if value is None:
            return None
        try:
            int(value, 16)
            return value[-5:]
        except ValueError:
            raise ValidationError(f"Invalid address format: {value}")

    @field_validator("bar")
    @classmethod
    def validate_bar(cls, value: int | None) -> int | None:
        """Validate the bar."""
        if value is None:
            return None
        if value == 0:
            return 0
        if not 0 <= value <= 9:
            raise ValidationError(f"BAR number out of range: {value}")
        return value

    @field_validator("register_value")
    @classmethod
    def validate_register_value(cls, value: str | None) -> str | None:
        """Validate the register value."""
        if value is None:
            return None
        if value == "0":
            return "00000000"
        try:
            int(value, 16)
            return value[-8:]
        except ValueError as e:
            raise ValidationError(f"Invalid register value format: {value} - {e}")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: float | None) -> float | None:
        """Validate timestamp value."""
        if value is None:
            return None
        if value < 0:
            raise ValidationError("Timestamp cannot be negative")
        return value

    @classmethod
    def normalize_timestamp(cls, timestamp: float) -> int:
        """Strip the timestamp from a value and remove the first two integers."""
        seconds: str = str(timestamp)[-1]
        nanos: str = str(timestamp).split(".")[1].ljust(6, "0")
        values: int = int(f"{seconds}{nanos}")
        logger.info(f"Normalized timestamp: {values}")
        return values

    @classmethod
    def remove_0x(cls, value: str | None, address: str | None) -> str | None:
        """Remove the 0x prefix from a value."""
        if value is None and address is None:
            return None
        if value is not None:
            return value.replace("0x", "")
        if address is not None:
            return address.replace("0x", "")
        return value

    @classmethod
    def format_value(cls, value: str | None, is_address: bool = False) -> str | None:
        """Format hex values to proper width."""
        if value is None:
            return None
        try:
            num = int(value, 16)
            return f"{num:05X}" if is_address else f"{num:08X}"
        except ValueError:
            return None

    @staticmethod
    def calculate_bit_width(value: str | None) -> int:
        """Calculate required bit width for a value."""
        if not value:
            return 32
        try:
            num = int(value, 16)
            return max(num.bit_length(), 1)
        except ValueError:
            return 32

    @classmethod
    def read_values(cls, bar: int | None = None) -> list[str]:
        """Get all read values, optionally filtered by BAR."""
        return [
            data.value
            for data in cls._tracker.all_instances
            if data.operation == "R" and data.value is not None and (bar is None or data.bar == bar)
        ]

    @classmethod
    def write_values(cls, bar: int | None = None) -> list[str]:
        """Get all write values, optionally filtered by BAR."""
        return [
            data.value
            for data in cls._tracker.all_instances
            if data.operation == "W" and data.value is not None and (bar is None or data.bar == bar)
        ]

    @classmethod
    def addresses(cls, bar: int | None = None) -> list[str]:
        """Get all addresses, optionally filtered by BAR."""
        return [
            data.address
            for data in cls._tracker.all_instances
            if data.address is not None and (bar is None or data.bar == bar)
        ]
