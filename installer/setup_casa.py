#!/usr/bin/python

import sys
import os
import os.path
import json
import traceback
import ssl
import base64
import pyDes
import re
import urllib2

from urlparse import urlparse
from xml.etree import ElementTree

from setup import *
from pylib import Properties

cur_dir = os.path.dirname(os.path.realpath(__file__))

#TODO: add command line options with argprase

def get_properties(prop_fn, current_properties=None):
    if not current_properties:
        p = Properties.Properties()
    else:
        p = current_properties

    with open(prop_fn) as file_object:
        p.load(file_object)
    
    for k in p.keys():
        if p[k].lower() == 'true':
            p[k] == True
        elif p[k].lower() == 'false':
            p[k] == False

    return p


with open("/etc/gluu/conf/salt") as f:
    salt_property = f.read().strip()
    key = salt_property.split("=")[1].strip()

def unobscure(s):
    cipher = pyDes.triple_des(key)
    decrypted = cipher.decrypt(base64.b64decode(s), padmode=pyDes.PAD_PKCS5)
    return decrypted

class SetupCasa(object):

    def __init__(self, install_dir):
        self.install_dir = install_dir
        self.setup_properties_fn = os.path.join(self.install_dir, 'setup_casa.properties')
        self.savedProperties = os.path.join(self.install_dir, 'setup_casa.properties.last')

        # Change this to final version
        self.twilio_version = '7.17.0'
        self.jsmmp_version = '2.3.7'
        self.casa_version = '4.1.1.Final'
        self.casa_war_url = 'https://ox.gluu.org/maven/org/gluu/casa/{0}/casa-{0}.war'.format(self.casa_version)
        self.twilio_jar_url = 'http://central.maven.org/maven2/com/twilio/sdk/twilio/{0}/twilio-{0}.jar'.format(self.twilio_version)

        self.application_max_ram = 1024  # in MB

        # Gluu components installation status
        self.install_oxd = False
        self.oxd_server_https = ""
        self.distFolder = '/opt/dist'
        self.casa = '/etc/gluu/conf/casa.json'
        self.jetty_app_configuration = {
            'casa': {'name': 'casa',
                                'jetty': {'modules': 'server,deploy,resources,http,http-forwarded,console-capture,jsp'},
                                'memory': {'ratio': 1, "jvm_heap_ration": 0.7, "max_allowed_mb": 1024},
                                'installed': False
                                }
        }

        self.detectedHostname = setupObject.detect_hostname()
        self.ldif_scripts_casa = '%s/scripts_casa.ldif' % setupObject.outputFolder
        self.casa_config = '%s/casa.json' % setupObject.outputFolder
    


    def check_installed(self):

        if setupObject.check_installed():
            return os.path.exists('%s/casa.json' % setupObject.configFolder)
        else:
            print "\nPlease run './setup.py' to configure Gluu Server first!\n"
            sys.exit()

    def download_files(self):
        setupObject.logIt("Downloading files")
        
        # Casa is not part of CE package. We need to download it if needed
        for download_url in (self.casa_war_url, self.twilio_jar_url):
            fname = os.path.basename(download_url)
            if fname.startswith('casa'):
                fname = 'casa.war'
            dest_path = os.path.join(setupObject.distGluuFolder, fname)
            if not os.path.exists(dest_path):
                print "Downloading:", fname
                setupObject.run(['/usr/bin/wget', download_url, '--no-verbose', '--retry-connrefused', '--tries=10', '-O', dest_path])

    def check_oxd_server(self, oxd_url, error_out=True):

        oxd_url = os.path.join(oxd_url, 'health-check')
        try:
            result = urllib2.urlopen(
                        oxd_url,
                        timeout = 2,
                        context=ssl._create_unverified_context()
                    )
            if result.code == 200:
                oxd_status = json.loads(result.read())
                if oxd_status['status'] == 'running':
                    return True
        except Exception as e:
            if error_out:
                print colors.DANGER
                print "Can't connect to oxd-server with url {}".format(oxd_url)
                print "Reason: ", e
                print colors.ENDC

    def promptForProperties(self):

        promptForLicense = setupObject.getPrompt("\n\nDo you acknowledge that use of the Gluu Casa is under the Apache  License V2? (y/n)", "n")[0].lower()

        if promptForLicense == 'n':
            print("You must accept the Gluu License Agreement to continue. Exiting.\n")
            sys.exit()
                
        self.oxd_server_https = 'https://localhost:8443'
        use_local_oxd = False


        self.application_max_ram = setupObject.getPrompt("Enter maximum RAM for applications in MB", '1024')

        # check local oxd-server
        local_oxd_check = self.check_oxd_server(self.oxd_server_https, False)

        if local_oxd_check:
            use_local_oxd = setupObject.getPrompt(
                "Local oxd server is detected. Do you want to use local oxd server? (y/n)?"
                )
            if use_local_oxd[0].lower() == 'n':
                use_local_oxd = False

        if not use_local_oxd:
            print "Please enter URL of oxd-server if you have one, for example: https://oxd.mygluu.org:8443"
            if not local_oxd_check:
                print "Else leave blank to install oxd server locally."
            else:
                print "Enter {}q{} to quit installation".format(colors.BOLD, colors.ENDC)
            while True:
                oxd_server_https = raw_input("oxd Server URL: ").lower()
                
                if oxd_server_https and oxd_server_https[0].lower() == 'q':
                    sys.exit()
                
                if (not oxd_server_https) and (not local_oxd_check):
                    self.install_oxd = True
                    break
                
                print "Checking oxd server"
                if self.check_oxd_server(oxd_server_https):
                    self.oxd_server_https = oxd_server_https
                    use_local_oxd = True
                    break

        if (not use_local_oxd) and (not self.install_oxd):
            print "An oxd server instance is required when installing this product via Linux packages."
            print "Exiting ..."
            sys.exit(0)

        print

    def casa_json_config(self):
        data = setupObject.readFile(self.casa_config)
        datastore = json.loads(data)

        o = urlparse(self.oxd_server_https)
        self.oxd_hostname = o.hostname
        self.oxd_port = o.port if o.port else 8443

        datastore['oxd_config']['host'] = self.oxd_hostname
        datastore['oxd_config']['port'] = self.oxd_port

        datastore_str = json.dumps(datastore, indent=2)
        setupObject.writeFile(self.casa, datastore_str)


    def import_ldif(self):
        
        p = get_properties(setupObject.gluu_properties_fn)

        if os.path.exists(setupObject.gluu_hybrid_roperties):
             get_properties(setupObject.gluu_hybrid_roperties, p)

        if p["persistence.type"] == 'couchbase' or p.get('storage.default') == 'couchbase':
            self.import_ldif_couchbase()
        elif p["persistence.type"] == 'ldap' or p.get('storage.default') == 'ldap':
            self.import_ldif_ldap()


    def import_ldif_couchbase(self):
        setupObject.logIt("Importing LDIF files into Couchbase")
        p = get_properties(setupObject.gluuCouchebaseProperties)
        attribDataTypes.startup(setupObject.install_dir)

        setupObject.oxtrust_admin_password = unobscure(p['auth.userPassword'])

        setupObject.prepare_multivalued_list()
        setupObject.cbm = CBM(p['servers'].split(',')[0], p['auth.userName'], setupObject.oxtrust_admin_password)
        setupObject.import_ldif_couchebase([os.path.join('.','output/scripts_casa.ldif')],'gluu')


    def import_ldif_ldap(self):
        setupObject.logIt("Importing LDIF files into LDAP")
        
        if not os.path.exists(setupObject.gluu_properties_fn):
            sys.exit("ldap properties file does not exist on this server. Terminating installation.")

        p = get_properties(setupObject.ox_ldap_properties)

        setupObject.ldapPass = unobscure(p['bindPassword'])
        setupObject.oxtrust_admin_password = setupObject.ldapPass
        setupObject.ldap_hostname = p['servers'].split(',')[0].split(':')[0]

        setupObject.createLdapPw()
        setupObject.ldap_binddn = "cn=directory manager"
        setupObject.import_ldif_template_opendj(self.ldif_scripts_casa)
        setupObject.deleteLdapPw()


    def install_oxd_server(self):

        print "\nInstalling oxd from package..."
        packageRpm = True
        packageExtension = ".rpm"
        if setupObject.os_type in ['debian', 'ubuntu']:
            packageRpm = False
            packageExtension = ".deb"

        oxdDistFolder = "%s/%s" % (self.distFolder, "oxd")

        if not os.path.exists(oxdDistFolder):
            setupObject.logIt(oxdDistFolder+" Directory is not found")
            print oxdDistFolder+" Directory is not found"
            sys.exit(0)

        packageName = None
        for file in os.listdir(oxdDistFolder):
            if file.endswith(packageExtension):
                packageName = "%s/%s" % ( oxdDistFolder, file )

        if packageName == None:
            setupObject.logIt('Failed to find oxd package in folder %s !' % oxdDistFolder)
            sys.exit(0)

        setupObject.logIt("Found package '%s' for install" % packageName)

        if packageRpm:
            setupObject.run([setupObject.cmd_rpm, '--install', '--verbose', '--hash', packageName])
        else:
            setupObject.run([setupObject.cmd_dpkg, '--install', packageName])

        #set trust_all_certs: true in oxd-server.yml 
        oxd_yaml_fn ='/opt/oxd-server/conf/oxd-server.yml'
        oxd_yaml = setupObject.readFile(oxd_yaml_fn).split('\n')
        
        for i, l in enumerate(oxd_yaml[:]):
            if l.strip().startswith('trust_all_certs'):
                oxd_yaml[i] = 'trust_all_certs: true'
        
        setupObject.writeFile(oxd_yaml_fn, '\n'.join(oxd_yaml))

        # Enable service autoload on Gluu-Server startup
        setupObject.enable_service_at_start('oxd-server')
        # change start.sh permission
        setupObject.run(['chmod', '+x', '/opt/oxd-server/bin/oxd-start.sh'])
        
        # Start oxd-server
        self.start_oxd_server()

    def start_oxd_server(self, cmd='start'):
        print "Starting oxd-server..."
        setupObject.run_service_command('oxd-server', cmd)


    def install_casa(self):
        print "Installing Casa"
        setupObject.logIt("Configuring Casa...")
        
        setupObject.calculate_aplications_memory(self.application_max_ram, 
                                                 self.jetty_app_configuration,
                                                 [self.jetty_app_configuration['casa']],
                                                )

        setupObject.copyFile('%s/casa.json' % setupObject.outputFolder, setupObject.configFolder)
        setupObject.run(['chmod', 'g+w', '/opt/gluu/python/libs'])

        setupObject.logIt("Copying casa.war into jetty webapps folder...")

        jettyServiceName = 'casa'
        setupObject.installJettyService(self.jetty_app_configuration[jettyServiceName])

        jettyServiceWebapps = '%s/%s/webapps' % (setupObject.jetty_base, jettyServiceName)
        setupObject.copyFile('%s/casa.war' % setupObject.distGluuFolder, jettyServiceWebapps)

        jettyServiceOxAuthCustomLibsPath = '%s/%s/%s' % (setupObject.jetty_base, "oxauth", "custom/libs")
        setupObject.copyFile(
                os.path.join(setupObject.distGluuFolder, os.path.basename(self.twilio_jar_url)), 
                jettyServiceOxAuthCustomLibsPath
                )
        
        setupObject.copyFile(
                os.path.join(setupObject.distGluuFolder, 'jsmpp-{}.jar'.format(self.jsmmp_version)), 
                jettyServiceOxAuthCustomLibsPath
                )
        
        setupObject.run([setupObject.cmd_chown, '-R', 'jetty:jetty', jettyServiceOxAuthCustomLibsPath])

        # Make necessary Directories for Casa
        for path in ('/opt/gluu/jetty/casa/static/', '/opt/gluu/jetty/casa/plugins'):
            if not os.path.exists(path):
                setupObject.run(['mkdir', '-p', path])
                setupObject.run(['chown', '-R', 'jetty:jetty', path])
        
        #Adding twilio jar path to oxauth.xml
        oxauth_xml_fn = '/opt/gluu/jetty/oxauth/webapps/oxauth.xml'
        if os.path.exists(oxauth_xml_fn):
            
            class CommentedTreeBuilder(ElementTree.TreeBuilder):
                def comment(self, data):
                    self.start(ElementTree.Comment, {})
                    self.data(data)
                    self.end(ElementTree.Comment)

            parser = ElementTree.XMLParser(target=CommentedTreeBuilder())
            tree = ElementTree.parse(oxauth_xml_fn, parser)
            root = tree.getroot()

            xml_headers = '<?xml version="1.0"  encoding="ISO-8859-1"?>\n<!DOCTYPE Configure PUBLIC "-//Jetty//Configure//EN" "http://www.eclipse.org/jetty/configure_9_0.dtd">\n\n'

            for element in root:
                if element.tag == 'Set' and element.attrib.get('name') == 'extraClasspath':
                    break
            else:
                element = ElementTree.SubElement(root, 'Set', name='extraClasspath')
                element.text = ''

            extraClasspath_list = element.text.split(',')

            for ecp in extraClasspath_list[:]:
                if (not ecp) or re.search('twilio-(.*)\.jar', ecp) or re.search('jsmpp-(.*)\.jar', ecp):
                    extraClasspath_list.remove(ecp)

            extraClasspath_list.append('./custom/libs/twilio-{}.jar'.format(self.twilio_version))
            extraClasspath_list.append('./custom/libs/jsmpp-{}.jar'.format(self.jsmmp_version))
            element.text = ','.join(extraClasspath_list)

            setupObject.writeFile(oxauth_xml_fn, xml_headers+ElementTree.tostring(root))

        setupObject.run(['chown', '-R', 'jetty:jetty', '%s/casa.json' % setupObject.configFolder])
        setupObject.run(['chmod', 'g+w', '%s/casa.json' % setupObject.configFolder])
        self.casa_json_config()
        

    def start_services(self):

        # Restart oxAuth service to load new custom libs
        print "\nRestarting oxAuth"
        try:
            setupObject.run_service_command('oxauth', 'restart')
            print "oxAuth restarted!\n"
        except:
            print "Error starting oxAuth! Please review setup_casa_error.log."
            setupObject.logIt("Error starting oxAuth", True)
            setupObject.logIt(traceback.format_exc(), True)

        # Start Casa
        print "Starting Casa..."
        try:
            setupObject.run_service_command('casa', 'start')
            print "Casa started!\n"
        except:
            print "Error starting Casa! Please review setup_casa_error.log."
            setupObject.logIt("Error starting Casa", True)
            setupObject.logIt(traceback.format_exc(), True)

    def import_oxd_certificate2javatruststore(self):
        setupObject.logIt("Importing oxd certificate")
        oxd_cert = ssl.get_server_certificate((self.oxd_hostname, self.oxd_port))
        oxd_alias = 'oxd_' + self.oxd_hostname.replace('.','_')
        oxd_cert_tmp_fn = '/tmp/{}.crt'.format(oxd_alias)

        with open(oxd_cert_tmp_fn,'w') as w:
            w.write(oxd_cert)

        setupObject.run(['/opt/jre/jre/bin/keytool', '-import', '-trustcacerts', '-keystore', 
                        '/opt/jre/jre/lib/security/cacerts', '-storepass', 'changeit', 
                        '-noprompt', '-alias', oxd_alias, '-file', oxd_cert_tmp_fn])

    def load_properties(self, fn):
        setupObject.logIt('Loading Properties %s' % fn)
        p = get_properties(fn)

        for k in p.keys():
            setattr(self, k, p[k])

if __name__ == '__main__':


    setupObject = Setup(cur_dir)
    setupObject.log = os.path.join(cur_dir, 'setup_casa.log')
    setupObject.logError = os.path.join(cur_dir, 'setup_casa_error.log')

    installObject = SetupCasa(cur_dir)

    if installObject.check_installed():
        print "\033[91m\nThis instance has already been configured. If you need to install new one you should reinstall package first.\033[0m"
        sys.exit(2)

    # Get the OS and init type
    (setupObject.os_type, setupObject.os_version) = setupObject.detect_os_type()
    setupObject.os_initdaemon = setupObject.detect_initd()
    
    print "\nInstalling Gluu Casa...\n"
    print "Detected OS  :  %s %s" % (setupObject.os_type, setupObject.os_version)
    print "Detected init:  %s" % setupObject.os_initdaemon

    setupObject.logIt("Installing Gluu Casa")

    if os.path.exists(installObject.setup_properties_fn):
        installObject.load_properties(installObject.setup_properties_fn)
    else:
        installObject.promptForProperties()

    try:
        installObject.download_files()

        if installObject.install_oxd:
            installObject.install_oxd_server()

        installObject.install_casa()
        installObject.import_ldif()
        installObject.import_oxd_certificate2javatruststore()
        installObject.start_services()
        setupObject.save_properties(installObject.savedProperties, installObject)
        
        print ("Encrypted properties file saved to {0}.enc with password {1}\n"
                "Decrypt the file with the following command if you want to "
                "re-use:\nopenssl enc -d -aes-256-cbc -in {2}.enc -out {3}\n"
                ).format( 
                    installObject.savedProperties,  
                    setupObject.oxtrust_admin_password, 
                    os.path.basename(installObject.savedProperties), 
                    os.path.basename(installObject.savedProperties)
                    )
    except:
        setupObject.logIt("***** Error caught in main loop *****", True)
        setupObject.logIt(traceback.format_exc(), True)


    print "Gluu Casa installation successful!\nPoint your browser to https://%s/casa\n" % installObject.detectedHostname
    print "Recall admin capabilities are disabled by default.\nCheck casa docs to learn how to unlock admin features\n"

