MOCKED_DEVICE_VENDOR_DIR = src/mocked_device
MOCKED_DEVICE_SOURCE_DIR = ../mocked-device/src/mocked_device
VERSION = 0.0.0
PKG_NAME = system-stub
BUILD_DIR = deb_dist/$(PKG_NAME)_$(VERSION)
OPT_DIR = $(BUILD_DIR)/opt/system-stub
PACKAGE = $(BUILD_DIR).deb
SOURCES = \
	system-stub.service \
	env.conf \
	override.conf \
	pyproject.toml \
	requirements.txt \

all: $(PACKAGE)

dist: clean
	mkdir -p $(OPT_DIR)/src
	@echo Import mocked_device as vendor package:
	cp -r $(MOCKED_DEVICE_SOURCE_DIR) $(OPT_DIR)/$(MOCKED_DEVICE_VENDOR_DIR)
	cp -r src/system_stub $(OPT_DIR)/src/system_stub
	cp -r DEBIAN $(BUILD_DIR)
	cp -r $(SOURCES) $(OPT_DIR)

$(PACKAGE): dist
	dpkg-deb --build $(BUILD_DIR)

install: $(PACKAGE)
	sudo apt install ./$<

clean:
	rm -r deb_dist ||:
