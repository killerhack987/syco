#!/usr/bin/env python
'''
Install glassfish with optimizations, security and common plugins.

Read more
http://docs.sun.com/app/docs/coll/1343.13?l=en
http://docs.sun.com/app/docs/doc/821-1757/aboaa?l=en&a=view
http://docs.sun.com/app/docs/doc/821-1751?l=en
http://www.nabisoft.com/tutorials/glassfish/installing-glassfish-301-on-ubuntu
http://iblog.humani-tech.com/?p=505
http://www.java.net/forums/glassfish/glassfish

TODO
See bottom of file

Changelog:
2011-01-30 - Daniel Lindh - Refactoring the use off class Version.
2011-01-29 - Daniel Lindh - Adding file header and comments
'''

__author__ = "daniel.lindh@cybercow.se"
__copyright__ = "Copyright 2011, The syscon project"
__maintainer__ = "Daniel Lindh"
__email__ = "daniel.lindh@cybercow.se"
__credits__ = ["???"]
__license__ = "???"
__version__ = "1.0.0"
__status__ = "Production"

import os, time, stat, shutil, traceback, sys, re
import app, general, version

# The version of this module, used to prevent
# the same script version to be executed more then
# once on the same host.
SCRIPT_VERSION = 1

GLASSFISH_PATH = "/usr/local/glassfish/"
GLASSFISH_DOMAINS_PATH = "/usr/local/glassfish/glassfish/domains/"

def build_commands(commands):
  '''
  Defines the commands that can be executed through the fosh.py shell script.

  '''
  commands.add("install-glassfish",   install_glassfish,  help="Install glassfish3 on the current server.")
  commands.add("uninstall-glassfish", uninstall_glassfish, help="Uninstall glassfish3 on the current server.")

def install_glassfish(args):
  '''
  The main installation function the for the glassfish, dependencies and plugins.

  '''
  app.print_verbose("Install glassfish3 version: %d" % SCRIPT_VERSION)
  version_obj = version.Version("InstallGlassfish", SCRIPT_VERSION)
  version_obj.check_executed()

  try:

    general.create_install_dir()

    #os.environ["JAVA_HOME"] = "/usr/java/latest"
    #os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]
    general.set_config_property("/etc/profile", 'export JAVA_HOME=/usr/java/latest',  'export JAVA_HOME=/usr/java/latest')
    general.set_config_property("/etc/profile", 'export PATH=$PATH:/usr/java/latest/bin',  'export PATH=$PATH:/usr/java/latest/bin')

    #_set_iptables()
    _install_software()

    for domain_name, port_base in [["domain1", "6000"], ["domain2", "7000"]]:
      admin_port=str(int(port_base)+48)
      _create_domains(domain_name, port_base)
      _set_domain_passwords(domain_name, admin_port)
      _set_domain_configs(admin_port)
      _set_jvm_options(admin_port)
      _install_domains_plugins(domain_name)

    # Restart to take effect
    general.shell_exec("/etc/init.d/glassfish restart")

    _update_glassfish()

    version_obj.mark_executed()
  except Exception, error_text:
    app.print_error("Failed to install glassfish")
    app.print_error(error_text)
    traceback.print_exc(file=sys.stdout)

  general.delete_install_dir()

def uninstall_glassfish(args):
  '''
  The main function the glassfish uninstallation.

  '''
  app.print_verbose("Uninstall glassfish3 version: %d" % SCRIPT_VERSION)

  os.chdir("/tmp")

  if (_is_glassfish_user_installed()):
    general.shell_exec("/etc/init.d/glassfish stop", user="glassfish")
    general.shell_exec("rm -rf /usr/local/glassfish")
    general.shell_exec("rm -rf /home/glassfish")

    general.shell_exec("chkconfig --del glassfish")
    general.shell_exec("rm /etc/init.d/glassfish")
    general.shell_exec("userdel glassfish")
    general.shell_exec("groupdel glassfishadm")

  if (os.access("/usr/java/jdk1.6.0_22", os.F_OK)):
    general.shell_exec("rpm -e sun-javadb-core-10.5.3-0.2")
    general.shell_exec("rpm -e sun-javadb-client-10.5.3-0.2")
    general.shell_exec("rpm -e  sun-javadb-demo-10.5.3-0.2")
    general.shell_exec("rpm -e sun-javadb-docs-10.5.3-0.2")
    general.shell_exec("rpm -e sun-javadb-javadoc-10.5.3-0.2")
    general.shell_exec("rpm -e sun-javadb-common-10.5.3-0.2")
    general.shell_exec("rpm -e jdk-1.6.0_22-fcs")

#
# Public members
#
# Might be used by other modules.
#

def exec_asadmin(admin_port="", command=""):
  if (admin_port):
    return general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " " + command, user="glassfish")
  else:
    return general.shell_exec("/usr/local/glassfish/bin/asadmin " + command, user="glassfish")

#
# Options / private memembers
#

def _is_glassfish_user_installed():
  '''
  Check if glassfish user is installed.

  '''
  for line in open("/etc/passwd"):
    if "glassfish" in line:
      return True
  return False

def _install_software():
  '''
  Download and install java and glassfish

  '''
  if (not _is_glassfish_user_installed()):
    # Add a new group for glassfish administration.
    # This can be used for all users that should be able to
    # adminitrate glassfish.
    general.shell_exec("groupadd glassfishadm -g 550")

    # Give glassfish it's own user.
    general.shell_exec("adduser -m -r --shell /bin/bash -u150 -g550 glassfish")

  _install_jdk()
  _install_glassfish()
  _install_eclipselink()

def _install_jdk():
  '''
  Installation of the java sdk.

  '''
  jdk_install_dir="/usr/java/jdk1.6.0_22"
  jdk_install_file="jdk-6u22-linux-x64-rpm.bin"

  if (not os.access(jdk_install_dir, os.F_OK)):
    os.chdir("/tmp/install")
    if (not os.access(jdk_install_file, os.F_OK)):
      general.shell_exec("wget http://10.100.100.200/cobbler/repo_mirror/java/" + jdk_install_file, user="glassfish")
      time.sleep(1)
      os.chmod(jdk_install_file, stat.S_IXUSR|stat.S_IRUSR)

    if (os.access(jdk_install_file, os.F_OK)):
      general.shell_run("./" + jdk_install_file,
      events={
        "ename: " : "A\r\n",
        "Press Enter to continue....." : "\r\n\r\n",
        "timeout":"-1"
      })
    else:
      raise Exception("Not able to download " + jdk_install_file)

def _install_glassfish():
  '''
  Installation of the glassfish application server.

  TODO: Change to /usr/local/glassfish.3.0.1

  '''
  glassfish_install_dir="/usr/local/glassfish"
  if (not os.access(glassfish_install_dir + "/glassfish", os.F_OK)):
    os.chdir("/tmp/install")
    if (not os.access("glassfish-3.0.1-unix.sh", os.F_OK)):
      general.shell_exec("wget http://download.java.net/glassfish/3.0.1/release/glassfish-3.0.1-unix.sh", user="glassfish")
      time.sleep(1)

    # Create installation dir
    if (not os.access(glassfish_install_dir, os.F_OK)):
      os.mkdir(glassfish_install_dir)
      os.chmod(glassfish_install_dir, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IXGRP)
      os.chown(glassfish_install_dir, 150, 550)

    # Set executeion permissions and run the installation.
    os.chmod("glassfish-3.0.1-unix.sh", stat.S_IXUSR|stat.S_IRUSR)
    shutil.copy("/opt/fosh/var/glassfish/glassfish-3.0.1-unix-answer", "/tmp/install/glassfish-3.0.1-unix-answer")
    general.shell_exec("./glassfish-3.0.1-unix.sh -a glassfish-3.0.1-unix-answer -s", user="glassfish")

    # Install the start script
    if (not os.access("/etc/init.d/glassfish", os.F_OK)):
      shutil.copy("/opt/fosh/var/glassfish/glassfish", "/etc/init.d/glassfish")
      general.shell_exec("chmod 0755 /etc/init.d/glassfish")
      general.shell_exec("chkconfig --add glassfish")
      general.shell_exec("chkconfig --level 3 glassfish on")

  if (not os.access(glassfish_install_dir + "/glassfish/domains/domain1/config/domain.xml", os.F_OK)):
    raise Exception("Failed to install " + glassfish_install_dir)

  if (not os.access("/etc/init.d/glassfish", os.F_OK)):
    raise Exception("Failed to install /etc/init.d/glassfish")

def _install_eclipselink():
  '''
  http://www.eclipse.org/eclipselink
  http://wiki.eclipse.org/EclipseLink/Examples/JPA/GlassFishV3_Web_Tutorial
  http://blogs.sun.com/GlassFishPersistence/entry/updating_eclipselink_bundles_in_glassfish

  '''
  os.chdir("/tmp/install")
  if (not os.access("eclipselink-plugins-2.1.2.v20101206-r8635.zip", os.F_OK)):
    general.shell_exec("wget http://ftp.ing.umu.se/mirror/eclipse/rt/eclipselink/releases/2.1.2/eclipselink-plugins-2.1.2.v20101206-r8635.zip", user="glassfish")
    general.shell_exec("wget -qO eclipselink-plugins-2.1.2.v20101206-r8635.zip.sha1 http://www.eclipse.org/downloads/sums.php?file=/rt/eclipselink/releases/2.1.2/eclipselink-plugins-2.1.2.v20101206-r8635.zip&type=sha1", user="glassfish")
    time.sleep(1)
    sha1sum=general.shell_exec("sha1sum --check eclipselink-plugins-2.1.2.v20101206-r8635.zip.sha1", user="glassfish")
    if (r"eclipselink-plugins-2.1.2.v20101206-r8635.zip: OK" not in sha1sum):
      raise Exception("Invalid checksum for eclipselink")

  general.shell_exec("unzip -oq eclipselink-plugins-2.1.2.v20101206-r8635.zip")

  general.shell_exec("cp org.eclipse.persistence.antlr_2.1.2.v20101206-r8635.jar /usr/local/glassfish/glassfish/modules/org.eclipse.persistence.antlr.jar", user="glassfish")
  general.shell_exec("cp org.eclipse.persistence.jpa_2.1.2.v20101206-r8635.jar /usr/local/glassfish/glassfish/modules/org.eclipse.persistence.jpa.jar", user="glassfish")
  general.shell_exec("cp org.eclipse.persistence.asm_2.1.2.v20101206-r8635.jar /usr/local/glassfish/glassfish/modules/org.eclipse.persistence.asm.jar", user="glassfish")
  general.shell_exec("cp org.eclipse.persistence.jpa.modelgen_2.1.2.v20101206-r8635.jar /usr/local/glassfish/glassfish/modules/org.eclipse.persistence.jpa.modelgen.jar", user="glassfish")
  general.shell_exec("cp org.eclipse.persistence.core_2.1.2.v20101206-r8635.jar /usr/local/glassfish/glassfish/modules/org.eclipse.persistence.core.jar", user="glassfish")
  general.shell_exec("cp org.eclipse.persistence.oracle_2.1.2.v20101206-r8635.jar /usr/local/glassfish/glassfish/modules/org.eclipse.persistence.oracle.jar", user="glassfish")
  general.shell_exec("cp javax.persistence_2.0.1.v201006031150.jar /usr/local/glassfish/glassfish/modules/javax.persistence.jar", user="glassfish")

def _create_domains(domain_name, port_base):
  '''
  Creating two domains for each applications, one active and one passive.

  '''
  general.shell_exec("/usr/local/glassfish/bin/asadmin stop-domain " + domain_name, user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin delete-domain " + domain_name, user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin create-domain --portbase " + port_base + " --nopassword " + domain_name, user="glassfish")

def _set_domain_passwords(domain_name, admin_port):
  '''
  Security configuration

  '''
  general.shell_exec("/usr/local/glassfish/bin/asadmin stop-domain " + domain_name, user="glassfish")

  # Change master password, default=empty
  general.shell_run("/usr/local/glassfish/bin/asadmin change-master-password --savemasterpassword=true " + domain_name,
    user="glassfish",
    events={
      "Enter Current Master Password> " : "changeit\n",
      "Enter New_Master_Password password> " : app.get_glassfish_master_password() + "\n",
      "Enter New_Master_Password password again> " : app.get_glassfish_master_password() + "\n"
   }
  )

  # Create new cert for https
  os.chdir("/usr/local/glassfish/glassfish/domains/" + domain_name + "/config/")
  general.shell_exec("keytool -delete -alias s1as -keystore keystore.jks -storepass " + app.get_glassfish_master_password(), user="glassfish")
  general.shell_exec('keytool -keysize 2048 -genkey -alias s1as -keyalg RSA -dname "CN=Fareoffice,O=Fareoffice,L=Stockholm,S=Stockholm,C=Sweden" -validity 3650 -keypass ' + app.get_glassfish_master_password() + ' -keystore keystore.jks -storepass ' + app.get_glassfish_master_password(), user="glassfish")
  general.shell_exec("keytool -list -keystore keystore.jks -storepass " + app.get_glassfish_master_password(), user="glassfish")

  general.shell_exec("/usr/local/glassfish/bin/asadmin start-domain " + domain_name, user="glassfish")

  # Change admin password
  general.shell_run("/usr/local/glassfish/bin/asadmin --port " + admin_port + " change-admin-password",
    user="glassfish",
    events={
      '(?i)Enter admin user name \[default: admin\]> ': "admin\n",
      '(?i)Enter admin password> ': "\n",
      '(?i)Enter new admin password> ': app.get_glassfish_admin_password() + "\n",
      '(?i)Enter new admin password again> ': app.get_glassfish_admin_password() + "\n"
    }
  )

  # Stores login info for glassfish user in /home/glassfish/.asadminpass
  general.shell_run("/usr/local/glassfish/bin/asadmin --port " + admin_port + " login",
    user="glassfish",
    events={
      "Enter admin user name \[default: admin\]> " : "admin\n",
      "Enter admin password> " : app.get_glassfish_admin_password() + "\n"
    }
  )

def _set_domain_configs(admin_port):
  # Disable sending x-powered-by in http header (Glassfish obfuscation)
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " set server.network-config.protocols.protocol.http-listener-1.http.xpowered-by=false", user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " set server.network-config.protocols.protocol.http-listener-2.http.xpowered-by=false", user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " set server.network-config.protocols.protocol.admin-listener.http.xpowered-by=false", user="glassfish")

  # Disable auto-deployment
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " set server.admin-service.das-config.autodeploy-enabled=false", user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " set server.admin-service.das-config.dynamic-reload-enabled=false", user="glassfish")

def _install_domains_plugins(domain_name):
   _install_mysql_connector(domain_name)
   _install_google_guice(domain_name)

def _install_mysql_connector(domain_name):
  '''
  http://www.mysql.com/downloads/connector/j/

  '''
  os.chdir("/tmp/install")

  if (not os.access("mysql-connector-java-5.1.14.tar.gz", os.F_OK)):
    general.shell_exec("wget http://ftp.sunet.se/pub/unix/databases/relational/mysql/Downloads/Connector-J/mysql-connector-java-5.1.14.tar.gz", user="glassfish")
    general.shell_exec("wget http://ftp.sunet.se/pub/unix/databases/relational/mysql/Downloads/Connector-J/mysql-connector-java-5.1.14.tar.gz.asc", user="glassfish")
    time.sleep(1)

  general.shell_exec("gpg --keyserver keyserver.ubuntu.com --recv-keys 5072E1F5", user="glassfish")
  signature=general.shell_exec("gpg --verify mysql-connector-java-5.1.14.tar.gz.asc", user="glassfish")
  if (r'Good signature from "MySQL Package signing key (www.mysql.com) <build@mysql.com>"' not in signature):
    app.print_error("Invalid signature.")
    return

  # TODO: Should it be under /ext/.
  general.shell_exec("tar zxf mysql-connector-java-5.1.14.tar.gz", user="glassfish")
  general.shell_exec("cp mysql-connector-java-5.1.14/mysql-connector-java-5.1.14-bin.jar /usr/local/glassfish/glassfish/domains/" + domain_name + "/lib/ext/", user="glassfish")

def _install_google_guice(domain_name):
  '''
  http://code.google.com/p/google-guice/
  http://code.google.com/p/google-guice/downloads/list

  '''
  os.chdir("/tmp/install")
  if (not os.access("guice-2.0.zip", os.F_OK)):
    general.shell_exec("wget http://google-guice.googlecode.com/files/guice-2.0.zip", user="glassfish")
    time.sleep(1)
    general.shell_exec("unzip -oq guice-2.0.zip", user="glassfish")

  general.shell_exec("cp guice-2.0/guice-2.0.jar /usr/local/glassfish/glassfish/domains/" + domain_name + "/lib/ext/", user="glassfish")
  general.shell_exec("cp guice-2.0/guice-assistedinject-2.0.jar /usr/local/glassfish/glassfish/domains/" + domain_name + "/lib/ext/", user="glassfish")
  general.shell_exec("cp guice-2.0/aopalliance.jar /usr/local/glassfish/glassfish/domains/" + domain_name + "/lib/ext/", user="glassfish")

def _set_jvm_options(admin_port):
  '''
  Change JVM Options used by glassfish

  # http://blogs.sun.com/watt/resource/jvm-options-list.html
  # http://www.oracle.com/technetwork/java/javase/tech/vmoptions-jsp-140102.html

  '''
  min_heap="512m"
  max_heap="1024m"
  max_perm_heap_size="512m"

  # List current jvm options
  general.shell_run("/usr/local/glassfish/bin/asadmin --port " + admin_port + " list-jvm-options",
    user="glassfish",
    events={'(?i)Do you trust the above certificate [y|N] -->': "y\n"}
  )

  # It's a server not a client.
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " delete-jvm-options -client", user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options -server", user="glassfish")

  # Change min and max heap space (ordinary heap = app objects)
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " delete-jvm-options -Xmx512m", user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options -Xmx" + max_heap, user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options -Xms" + min_heap, user="glassfish")

  # (perm heap = app class definitions)
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " delete-jvm-options '-XX\:MaxPermSize=192m'", user="glassfish")
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options '-XX\:MaxPermSize=" + max_perm_heap_size + "'", user="glassfish")

  # http://wikis.sun.com/display/HotSpotInternals/CompressedOops
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options '-XX\:+UseCompressedOops'", user="glassfish")

  # Use optimized versions of Get<Primitive>Field.
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options '-XX\:+UseFastAccessorMethods'", user="glassfish")

  # http://en.wikipedia.org/wiki/Escape_analysis
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options '-XX\:+DoEscapeAnalysis'", user="glassfish")

  # http://www.oracle.com/technetwork/java/javase/tech/vmoptions-jsp-140102.html
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options '-XX\:+AggressiveOpts'", user="glassfish")

  # Get rid of http header field value "server" (Glassfish obfuscation)
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options -Dproduct.name=\"\"", user="glassfish")

  # Security: Disable the stacktrace for SOAP fault message
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options -Dcom.sun.xml.ws.fault.SOAPFaultBuilder.disableCaptureStackTrace=true", user="glassfish")

  #
  # Tell glassfish-gui that it is not allowed to connect to internet.
  # http://java.net/jira/browse/GLASSFISH-14243
  # http://markmail.org/message/7mykjbd5i6mv6ckj?q=sun.enterprise.tools.admingui.NO_NETWORK#query:sun.enterprise.tools.admingui.NO_NETWORK+page:1+mid:fav63oofenom3gxk+state:results
  # http://serverfault.com/questions/103780/how-to-stop-openesb-glassfish-admin-console-from-opening-connection-to-glassfishe
  #
  #    * Regardless of registration state, there will be no popup reminder,
  #      no registration tree node, no Registartion in common task.
  #    * GlassFish News will not be shown in the tree node nor the common
  #      task page
  #    * The information frame under Common Task page will not be rendered.
  #
  general.shell_exec("/usr/local/glassfish/bin/asadmin --port " + admin_port + " create-jvm-options -Dcom.sun.enterprise.tools.admingui.NO_NETWORK=true", user="glassfish")

def _update_glassfish():
  '''
  Update the installed glassfish

  More info
  http://docs.sun.com/app/docs/doc/821-1751/ghapp?l=en&a=view

  '''
  # pkg refresh must be in a writeable dir.
  os.chdir("/tmp")

  general.shell_exec("yum -y install libidn")
  general.shell_run("/usr/local/glassfish/bin/pkg refresh --full",
    user="glassfish",
    events={
      re.compile('Would you like to install this software now [(]y[/]n[)][:].*'): "y\r\n"
    }
  )
  general.shell_exec("chcon -f -t textrel_shlib_t /usr/local/glassfish/pkg/vendor-packages/OpenSSL/crypto.so")

  # Need to run a second time, in the first run the pkg software might
  # have been installed, and after that the chcon needs to be executed
  # and after that the real pkg refresh needs to be executed
  general.shell_run("/usr/local/glassfish/bin/pkg refresh --full",
    user="glassfish",
    events={
      re.compile('Would you like to install this software now [(]y[/]n[)][:].*'): "y\r\n"
    }
  )

  general.shell_exec("/etc/init.d/glassfish stop")
  general.shell_exec("/usr/local/glassfish/bin/pkg image-update", user="glassfish")
  general.shell_exec("/etc/init.d/glassfish start")

def _set_iptables():
  pass
#  #
#  # Setup all iptable rules
#  #
#  4848 Administration Console
#  8080 HTTP
#  8081 HTTPS
#  8686 Pure JMX clients
#  3700 IIOP
#  3820 IIOP/SSL
#  3920 IIOP/SSL with mutual authentication
#
#  # ATTENTION: flush/delete all existing rules
#  iptables -F
#
#  ################################################################
#  # set the default policy for each of the pre-defined chains
#  ################################################################
#  iptables -P INPUT ACCEPT
#  iptables -P OUTPUT ACCEPT
#  iptables -P FORWARD DROP
#
#  # allow establishment of connections initialised by my outgoing packets
#  iptables -A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
#
#  # accept anything on localhost
#  iptables -A INPUT -i lo -j ACCEPT
#
#  ################################################################
#  #individual ports tcp
#  ################################################################
#  iptables -A INPUT -p tcp --dport 80 -j ACCEPT
#  iptables -A INPUT -p tcp --dport 22 -j ACCEPT
#  iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
#  iptables -A INPUT -p tcp --dport 8181 -j ACCEPT
#  iptables -A INPUT -p tcp --dport 443 -j ACCEPT
#  #uncomment next line to enable AdminGUI on port 4848:
#  iptables -A INPUT -p tcp --dport 4848 -j ACCEPT
#
#  ################################################################
#  #slow the amount of ssh connections by the same ip address:
#  #wait 60 seconds if 3 times failed to connect
#  ################################################################
#  iptables -I INPUT -p tcp -i eth0 --dport 22 -m state --state NEW -m recent --name sshprobe --set -j ACCEPT
#  iptables -I INPUT -p tcp -i eth0 --dport 22 -m state --state NEW -m recent --name sshprobe --update --seconds 60 --hitcount 3 --rttl -j DROP
#
#  #drop everything else
#  iptables -A INPUT -j DROP
#
#  ################################################################
#  #Redirection Rules
#  ################################################################
#  #1. redirection rules (allowing forwarding from localhost)
#  iptables -t nat -A OUTPUT -o lo -p tcp --dport 80 -j REDIRECT --to-port 8080
#  iptables -t nat -A OUTPUT -o lo -p tcp --dport 443 -j REDIRECT --to-port 8181
#
#  #2. redirection http
#  iptables -t nat -A PREROUTING -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 8080
#
#  #3. redirection https
#  iptables -t nat -A PREROUTING -p tcp -m tcp --dport 443 -j REDIRECT --to-ports 8181
#
#
#  ################################################################
#  #save the rules somewhere and make sure
#  #our rules get loaded if the ubuntu server is restarted
#  ################################################################
#  iptables-save > /etc/my-iptables.rules
#  iptables-restore < /etc/my-iptables.rules
#
#  #List Rules to see what we have now
#  iptables -L

#
# Questions?
#* Ska vi kora fo och fp pa samma server cluster?
#  2 domaner for fo, och tva domaner for fp?
#
#  Separata serverar
#  + Miljoerna kan inte pa nagot satt paverka varandra.
#
#  Gemensama servrar
#  + Utnyttjar alla servrar battre, cpu, disk och minne for virtualisering och OS blir mindre.
#  + Far battre lastbalansering/failover
#  + Vi kan strunta i vmware pa mysql och glassfish server.
#
#  * Varje doman har tilldelat minne, sa det spelar ingen roll
#    om det ligger pa samma eller separata servrar.

#

#
# Configure virutal servers/virtual hosts?
#

# Change folder where logs are stored
#
#http://docs.sun.com/app/docs/doc/821-1751/abluj?l=en&a=view
#
#stop glassfish
#vi /usr/local/glassfish/glassfish/domains/domain1/config/logging.properties
#change .sun.enterprise.server.logging.GFFileHandler.file
#
# Check if the log files are to big, backup, rotate.
#

#
# Kolla av olika profiler (develop/cluster/enterprise)
#

#
# http://docs.sun.com/app/docs/doc/821-1751/ghcjc?l=en&a=view
# asadmin> create-system-properties http-listener-port=1088
#

#
# For the monitor softare, to check if anything has changed.
# It exist a monitor thing in the admin console
#
#tror det finns ett kommando som gor att resultatet ar mer latt parsat.
#asadmin> list-system-properties
#asadmin> list-applications --type web
#asadmin> list-containers
#asadmin> list-modules
#asadmin> list-commands --localonly
#asadmin> list-timers server
#asadmin> show-component-status MEjbApp
#asadmin> uptime
#asadmin> generate-jvm-report --type summary
#asadmin> list-logger-levels
#
#Check for more monitor data.
#http://docs.sun.com/app/docs/doc/821-1751/ablur?l=en&a=view
#

#
# Optimizations
# http://www.oracle.com/technetwork/java/javase/tech/vmoptions-jsp-140102.html
#

#
# Setup Thread pools
#
#http://docs.sun.com/app/docs/doc/821-1751/abluc?l=en&a=view
#asadmin> list-threadpools
#

#
# Something to read.
#
# http://kalali.me/learning-glassfish-v3-command-line-administration-interface-cli/

#
# change /opt/glassfishv3/glassfish/domains/domain1/config/domain.xml
# Didn't get this to work. Need to use --secure on all asadmin.
# Maybe it works in glassfish 3.1
# The creates ssl connection between asadmin and DAS or other nodes
# TODO:general.shell_exec("/usr/local/glassfish/bin/asadmin set server-config.network-config.protocols.protocol.admin-listener.security-enabled=true", user="glassfish")
#

#
# Something in glassfish might need this, according to install requriments.
#
# yum install compat-libstdc++ compat-libgcc
#

#
# Extending and Updating GlassFish Server Inside a Closed Network
#
# http://docs.sun.com/app/docs/doc/821-1751/gjcya?l=en&a=view
#

# Log to syslog instead??
# com.sun.enterprise.server.logging.SyslogHandler.useSystemLogging=true

#
# Turn on proxy
# Might be useful if the server is locked down, and need to reach internet.
# http://download.oracle.com/javase/6/docs/technotes/guides/net/proxies.html
# /usr/local/glassfish/bin/asadmin create-jvm-options -Dhttp.proxyHost=my.proxy.host
# /usr/local/glassfish/bin/asadmin create-jvm-options -Dhttp.proxyPort=3128
#