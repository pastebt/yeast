FULL_VER=0.1
BUILD_NO=1

NAME=yeast

pdir=$(NAME)-$(FULL_VER).$(BUILD_NO)
pkg=$(pdir).tgz
srcpkg=$(pdir)-src.tgz
idir=$(PREFIX)/usr/share/$(NAME)

rpmtop=/tmp/rpmtop

install_filelist= setup.sh

all: py

py:
	@echo version = $(FULL_VER), build = $(BUILD_NO)

clean:
	@rm -f $(pkg)
	@rm -f $(srcpkg)
	@rm -f ./yeast/*.py? ./demo/*.py? ./testcase/*.py?
	@rm -f $(NAME)-$(FULL_VER)-*.rpm

install_py:
	@mkdir -p $(idir) && cp -r $(install_filelist) $(idir)
	@mv yeast $(idir)/src
	@sed -i s%__VERSION__%$(FULL_VER).$(BUILD_NO)% $(idir)/src/__init__.py

source:
	@make clean
	@tar cvfz $(srcpkg) $(install_filelist) ./yeast Makefile $(NAME).spec --exclude .git*

rpm:
	@cd ./testcase; python all_test.py
	@mkdir -p $(rpmtop) && cd $(rpmtop) && mkdir -p BUILD SOURCES SPECS RPMS SPRMS
	@tar cvfz $(rpmtop)/SOURCES/$(NAME)-src.tar.gz . ../yeast --exclude .git*
	@rpmbuild --define '_topdir $(rpmtop)' --define 'version $(FULL_VER)' --define 'build_no $(BUILD_NO)' --define 'pkgname $(NAME)' -bb $(NAME).spec
	@mv `find $(rpmtop)/RPMS/ -name '$(NAME)-$(FULL_VER)-*.rpm'` .


