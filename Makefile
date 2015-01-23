FULL_VER='$(shell grep '^Version' RELEASE.NOTES|head -1|cut -d , -f1|cut -d ' ' -f2)'
BUILD_NO='$(shell grep '^Version' RELEASE.NOTES|head -1|cut -d , -f2|cut -d ' ' -f3)'

NAME=yeast

pdir=$(NAME)-$(FULL_VER).$(BUILD_NO)
pkg=$(pdir).tgz
srcpkg=$(pdir)-src.tgz
idir=$(PREFIX)/usr/share/$(NAME)

rpmtop=/tmp/rpmtop

install_filelist= RELEASE.NOTES setup.sh

all: py

py:
	@echo version = $(FULL_VER), build = $(BUILD_NO)

clean:
	@rm -f $(pkg)
	@rm -f $(srcpkg)
	@rm -f ../yeast/*.pyc 
	@rm -f $(NAME)-$(FULL_VER)-*.rpm

install_py:
	@mkdir -p $(idir) && cp -r $(install_filelist) $(idir)
	@mv yeast $(idir)/src
	@sed -i s%__VERSION__%$(FULL_VER).$(BUILD_NO)% $(idir)/src/__init__.py

source:
	@make clean
	@tar cvfz $(srcpkg) $(install_filelist) ../yeast Makefile $(NAME).spec --exclude .hg

rpm:
	@cd ../testcase; python all_test.py
	@mkdir -p $(rpmtop) && cd $(rpmtop) && mkdir -p BUILD SOURCES SPECS RPMS SPRMS
	@tar cvfz $(rpmtop)/SOURCES/$(NAME)-src.tar.gz . ../yeast --exclude .hg
	@rpmbuild --define '_topdir $(rpmtop)' --define 'version $(FULL_VER)' --define 'build_no $(BUILD_NO)' --define 'pkgname $(NAME)' -bb $(NAME).spec
	@mv `find $(rpmtop)/RPMS/ -name '$(NAME)-$(FULL_VER)-*.rpm'` .


