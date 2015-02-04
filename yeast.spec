Summary: Yeast
License: GPL v2.0
Group: Development/Library
#pkgname define in Makefile
Name: %{pkgname}
Prefix: /usr
Provides: YEAST
Release: %{build_no}
Source: %{pkgname}-src.tar.gz
URL: http://www.fortinet.com/
# define in Makefile
Version: %{version}
BuildArch: noarch
Buildroot: /tmp/%{pkgname}rpm
#Autoreq: 0
#BuildRequires: python-devel
Requires: python > 2.6
%description 

#%define _source_filedigest_algorithm 0
#%define _binary_filedigest_algorithm 0

#%define __find_requires 0
#%define __find_provides 0
#%define __find_provides %{nil}


%prep
#%setup -q
%setup -c -n %{pkgname}-%{version}

%build
#./configure CXXFLAGS=-O3 --prefix=$RPM_BUILD_ROOT/usr
make

%install
rm -fr $RPM_BUILD_ROOT
make install_py PREFIX=$RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/usr/share/%{pkgname}/*
#%doc /usr/doc/jikes-%{version}/license.htm
#%doc /usr/man/man1/jikes.1* 

%pre
if [ "$1" -gt 1 ]; then # upgrade, remove old first
cd /usr/share/%{pkgname}
./setup.sh remove
fi

%post
cd /usr/share/%{pkgname}
./setup.sh install
exit 0

%preun
cd /usr/share/%{pkgname}
if [ "$1" == 0 ]; then # remove not for upgrade
./setup.sh remove
fi
exit 0

%postun
if [ "$1" == 0 ]; then # remove not for upgrade
rm -fr /usr/share/%{pkgname}
fi
exit 0


