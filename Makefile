NAME = pawnlib
GIT_USER = JINWOO-J
PRIMARY_BRANCH = master
BUILD_DATE = $(strip $(shell date -u +"%Y-%m-%dT%H:%M:%S%Z"))


define colorecho
      @tput setaf 6
      @echo $1
      @tput sgr0
endef

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    ECHO_OPTION = "-e"
    SED_OPTION =
endif
ifeq ($(UNAME_S),Darwin)
    ECHO_OPTION = ""
	SED_OPTION = ''
endif

NO_COLOR=\033[0m
OK_COLOR=\033[32m
ERROR_COLOR=\033[31m
WARN_COLOR=\033[93m

TEST_FILES := $(shell find tests -name '*.yml')
LOCAL_SERVER := "20.20.5.172"
VERSION := $(shell python3 -c "from pawnlib import __version__;print(__version__.__version__)")

#git_describe_ver = $(shell git describe --tags | sed -E -e 's/^v//' -e 's/(.*)-.*/\1/')

.PHONY: all build push test tag_latest release ssh bash

all: build upload
version:
	@echo $(VERSION)

print_version:
	@echo "$(OK_COLOR) VERSION-> $(VERSION)  REPO-> $(REPO_HUB)/$(NAME):$(TAGNAME) $(NO_COLOR) IS_LOCAL: $(IS_LOCAL)"

make_debug_mode:
	@$(shell echo $(ECHO_OPTION) "$(OK_COLOR) ----- DEBUG Environment ----- $(MAKECMDGOALS)  \n $(NO_COLOR)" >&2)\
		$(shell echo "" > DEBUG_ARGS) \
			$(foreach V, \
				$(sort $(.VARIABLES)), \
				$(if  \
					$(filter-out environment% default automatic, $(origin $V) ), \
						$($V=$($V)) \
					$(if $(filter-out "SHELL" "%_COLOR" "%_STRING" "MAKE%" "colorecho" ".DEFAULT_GOAL" "CURDIR" "TEST_FILES" , "$V" ),  \
						$(shell echo $(ECHO_OPTION) '$(OK_COLOR)  $V = $(WARN_COLOR) $($V) $(NO_COLOR) ' >&2;) \
						$(shell echo '-e $V=$($V)  ' >> DEBUG_ARGS)\
					)\
				)\
			)

make_build_args:
	@$(shell echo $(ECHO_OPTION) "$(OK_COLOR) ----- Build Environment ----- \n $(NO_COLOR)" >&2)\
	   $(shell echo "" > BUILD_ARGS) \
		$(foreach V, \
			 $(sort $(.VARIABLES)), \
			 $(if  \
				 $(filter-out environment% default automatic, $(origin $V) ), \
				 	 $($V=$($V)) \
				 $(if $(filter-out "SHELL" "%_COLOR" "%_STRING" "MAKE%" "colorecho" ".DEFAULT_GOAL" "CURDIR" "TEST_FILES", "$V" ),  \
					$(shell echo $(ECHO_OPTION) '$(OK_COLOR)  $V = $(WARN_COLOR) $($V) $(NO_COLOR) ' >&2;) \
				 	$(shell echo "--build-arg $V=$($V)  " >> BUILD_ARGS)\
				  )\
			  )\
		 )

test:   make_build_args print_version
		python3 -m unittest tests/test_*.py
		#python3 tests/test_*.py
#		shellcheck -S error src/*.sh
#		$(foreach TEST_FILE, $(TEST_FILES), \
#			container-structure-test test --driver docker --image $(REPO_HUB)/$(NAME):$(TAGNAME) \
#			--config $(TEST_FILE) || exit 1 ;\
#		)

clean:
	rm -rf build dist *.egg-info


build: make_build_args clean
		python3 setup.py bdist_wheel
		pip3 install dist/pawnlib-*.whl --force-reinstall

init:
		git init
		git add .
		git commit -m "first commit"
		git branch -M $(PRIMARY_BRANCH)
		git remote add origin git@github.com:$(GIT_USER)/$(NAME).git
		git push -u origin $(PRIMARY_BRANCH)


upload:
		python3 -m twine upload dist/* --verbose

gendocs:
	@$(shell ./makeMakeDown.sh)

local_deploy: build
	scp dist/pawnlib-$(VERSION)-py3-none-any.whl root@$(LOCAL_SERVER):/app/;
	ssh root@$(LOCAL_SERVER) pip3 install /app/pawnlib-$(VERSION)-py3-none-any.whl --force-reinstall

