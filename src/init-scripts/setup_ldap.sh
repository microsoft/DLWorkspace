{% if "ldap" in cnf %}
echo "Setup LDAP....."
if [ -n ${LDAP_BASE+x} ]; then 
    export LDAP_BASE="{{ cnf["ldap"]["ldap_base"] }}"
fi
if [ -n ${LDAP_URI+x} ]; then 
    export LDAP_URI="{{ cnf["ldap"]["ldap_uri"] }}"
fi
if [ -n ${LDAP_READ_ONLY_USER+x} ]; then 
    export LDAP_READ_ONLY_USER="{{ cnf["ldap"]["ldap_read_only_user"] }}"
fi
if [ -n ${LDAP_READ_ONLY_PASSWORD+x} ]; then 	
    export LDAP_READ_ONLY_PASSWORD="{{ cnf["ldap"]["ldap_read_only-password"] }}"
fi

sudo DEBIAN_FRONTEND=noninteractive apt install -yq libnss-ldap libpam-ldap ldap-utils

echo "base ${LDAP_BASE}" | sudo tee -a /etc/ldap.conf > /dev/null
echo "uri ${LDAP_URI}" | sudo tee -a /etc/ldap.conf > /dev/null
echo "binddn ${LDAP_READ_ONLY_USER}" | sudo tee -a /etc/ldap.conf > /dev/null
echo "bindpw ${LDAP_READ_ONLY_PASSWORD}" | sudo tee -a /etc/ldap.conf > /dev/null
echo "session required pam_mkhomedir.so umask=0022 skel=/etc/skel" | sudo tee -a /etc/pam.d/common-session > /dev/null

sudo sed -i -E 's/^passwd.*/& ldap/' /etc/nsswitch.conf
sudo sed -i -E 's/^group.*/& ldap/' /etc/nsswitch.conf
sudo sed -i -E 's/^shadow.*/& ldap/' /etc/nsswitch.conf
{% else %}
echo "No LDAP....."
{% endif %}
