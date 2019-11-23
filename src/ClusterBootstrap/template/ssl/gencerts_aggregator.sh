#!/bin/bash

# Downloads cfssl/cfssljson into $1 directory if they do not already exist in PATH
#
# Assumed vars:
#   $1 (cfssl directory) (optional)
#
# Sets:
#  CFSSL_BIN: The path of the installed cfssl binary
#  CFSSLJSON_BIN: The path of the installed cfssljson binary
#
function kube::util::ensure-cfssl {
  if command -v cfssl &>/dev/null && command -v cfssljson &>/dev/null; then
    CFSSL_BIN=$(command -v cfssl)
    CFSSLJSON_BIN=$(command -v cfssljson)
    return 0
  fi

  # Create a temp dir for cfssl if no directory was given
  local cfssldir=${1:-}
  if [[ -z "${cfssldir}" ]]; then
    kube::util::ensure-temp-dir
    cfssldir="${KUBE_TEMP}/cfssl"
  fi

  mkdir -p "${cfssldir}"
  pushd "${cfssldir}" > /dev/null

    echo "Unable to successfully run 'cfssl' from $PATH; downloading instead..."
    kernel=$(uname -s)
    case "${kernel}" in
      Linux)
        #curl --retry 10 -L -o cfssl https://pkg.cfssl.org/R1.2/cfssl_linux-amd64
        #curl --retry 10 -L -o cfssljson https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64
        cp ${DEPLOY_PATH}/../bin/other/cfssl .
        cp ${DEPLOY_PATH}/../bin/other/cfssljson .
        ;;
      Darwin)
        curl --retry 10 -L -o cfssl https://pkg.cfssl.org/R1.2/cfssl_darwin-amd64
        curl --retry 10 -L -o cfssljson https://pkg.cfssl.org/R1.2/cfssljson_darwin-amd64
        ;;
      *)
        echo "Unknown, unsupported platform: ${kernel}." >&2
        echo "Supported platforms: Linux, Darwin." >&2
        exit 2
    esac

    chmod +x cfssl || true
    chmod +x cfssljson || true

    CFSSL_BIN="${cfssldir}/cfssl"
    CFSSLJSON_BIN="${cfssldir}/cfssljson"
    if [[ ! -x ${CFSSL_BIN} || ! -x ${CFSSLJSON_BIN} ]]; then
      echo "Failed to download 'cfssl'. Please install cfssl and cfssljson and verify they are in \$PATH."
      echo "Hint: export PATH=\$PATH:\$GOPATH/bin; go get -u github.com/cloudflare/cfssl/cmd/..."
      exit 1
    fi
  popd > /dev/null
}

# Runs the easy RSA commands to generate aggregator certificate files.
# The generated files are in ${AGGREGATOR_CERT_DIR}
#
# Assumed vars
#   KUBE_TEMP
#   AGGREGATOR_MASTER_NAME
#   AGGREGATOR_CERT_DIR
#   AGGREGATOR_PRIMARY_CN: Primary canonical name
#   AGGREGATOR_SANS: Subject alternate names
#
#
function generate-aggregator-certs {
  # Note: This was heavily cribbed from make-ca-cert.sh
  (set -x
    cd "${KUBE_TEMP}/easy-rsa-master/aggregator"
    ./easyrsa init-pki
    # this puts the cert into pki/ca.crt and the key into pki/private/ca.key
    ./easyrsa --batch "--req-cn=${AGGREGATOR_PRIMARY_CN}@$(date +%s)" build-ca nopass
    ./easyrsa --subject-alt-name="${AGGREGATOR_SANS}" build-server-full "${AGGREGATOR_MASTER_NAME}" nopass
    ./easyrsa build-client-full aggregator-apiserver nopass

    kube::util::ensure-cfssl "${KUBE_TEMP}/cfssl"

    # make the config for the signer
    echo '{"signing":{"default":{"expiry":"43800h","usages":["signing","key encipherment","client auth"]}}}' > "ca-config.json"
    # create the aggregator client cert with the correct groups
    echo '{"CN":"aggregator","hosts":[""],"key":{"algo":"rsa","size":2048}}' | "${CFSSL_BIN}" gencert -ca=pki/ca.crt -ca-key=pki/private/ca.key -config=ca-config.json - | "${CFSSLJSON_BIN}" -bare proxy-client
    mv "proxy-client-key.pem" "pki/private/proxy-client.key"
    mv "proxy-client.pem" "pki/issued/proxy-client.crt"
    rm -f "proxy-client.csr"

    # Make a superuser client cert with subject "O=system:masters, CN=kubecfg"
    ./easyrsa --dn-mode=org \
      --req-cn=proxy-clientcfg --req-org=system:aggregator \
      --req-c= --req-st= --req-city= --req-email= --req-ou= \
      build-client-full proxy-clientcfg nopass)
  local output_file_missing=0
  local output_file
  for output_file in \
    "${AGGREGATOR_CERT_DIR}/pki/private/ca.key" \
    "${AGGREGATOR_CERT_DIR}/pki/ca.crt" \
    "${AGGREGATOR_CERT_DIR}/pki/issued/proxy-client.crt" \
    "${AGGREGATOR_CERT_DIR}/pki/private/proxy-client.key"
  do
    if [[ ! -s "${output_file}" ]]; then
      echo "Expected file ${output_file} not created" >&2
      output_file_missing=1
    else
      # NOTE(harry): copy files to destination folder
       cp "${output_file}" "${DEST_AGGREGATOR_CERT_DIR}"
    fi
  done
  if (( $output_file_missing )); then
    cat "${cert_create_debug_output}" >&2
    echo "=== Failed to generate aggregator certificates: Aborting ===" >&2
    exit 2
  fi
}

# Set up easy-rsa directory structure.
#
# Assumed vars
#   KUBE_TEMP
#
# Vars set:
#   CERT_DIR
#   AGGREGATOR_CERT_DIR
function setup-easyrsa {
  (set -x
    cd "${KUBE_TEMP}"
    # change away from using googleapis
    #curl -L -O --connect-timeout 20 --retry 6 --retry-delay 2 https://github.com/OpenVPN/easy-rsa/archive/v3.0.5.tar.gz
    # tar to easy-rsa-v3.0.5
    # this file is copied from docker image binstore, codes in deploy.py::get_other_binary()
    cp ${DEPLOY_PATH}/../bin/other/easy-rsa/v3.0.5.tar.gz .
    tar xzf v3.0.5.tar.gz
    mv easy-rsa-3.0.5 easy-rsa-master
    mkdir easy-rsa-master/kubelet
    cp -r easy-rsa-master/easyrsa3/* easy-rsa-master/kubelet
    mkdir easy-rsa-master/aggregator
    cp -r easy-rsa-master/easyrsa3/* easy-rsa-master/aggregator)
  CERT_DIR="${KUBE_TEMP}/easy-rsa-master/easyrsa3"
  AGGREGATOR_CERT_DIR="${KUBE_TEMP}/easy-rsa-master/aggregator"
  if [ ! -x "${CERT_DIR}/easyrsa" -o ! -x "${AGGREGATOR_CERT_DIR}/easyrsa" ]; then
    cat "${cert_create_debug_output}" >&2
    echo "=== Failed to setup easy-rsa: Aborting ===" >&2
    exit 2
  fi
}

# Create certificate pairs for the cluster.
# $1: The public IP for the master.
#
#
# Assumed vars
#   DNS_DOMAIN
#   MASTER_NAMES
#
function create-aggregator-certs {
  local -r primary_cn="${1}"

  # Determine extra certificate names for master
  local octets=($(echo "${SERVICE_CLUSTER_IP_RANGE}" | sed -e 's|/.*||' -e 's/\./ /g'))
  ((octets[3]+=1))
  local -r service_ip=$(echo "${octets[*]}" | sed 's/ /./g')
  local sans=""
  for extra in $@; do
    if [[ -n "${extra}" ]]; then
      sans="${sans}IP:${extra},"
    fi
  done
  sans="${sans}IP:${service_ip},DNS:kubernetes,DNS:kubernetes.default,DNS:kubernetes.default.svc,DNS:kubernetes.default.svc.${DNS_DOMAIN},${MASTER_NAMES}"

  echo "Generating certs for alternate-names: ${sans}"

  setup-easyrsa
  AGGREGATOR_PRIMARY_CN="${primary_cn}" AGGREGATOR_SANS="${sans}" generate-aggregator-certs
}


# Main function of this script.
export DEPLOY_PATH=$(pwd)
export KUBE_TEMP=$(mktemp --tmpdir=/tmp -d -t kubernetes.XXXXXX)
export AGGREGATOR_MASTER_NAME=aggregator
# DEST_AGGREGATOR_CERT_DIR is ./deploy/aggregator
export DEST_AGGREGATOR_CERT_DIR=aggregator

export SERVICE_CLUSTER_IP_RANGE={{cnf["service_cluster_ip_range"]}}
# apiserver_names_ssl_aggregator is set in GetCertificateProperty(), which is like: [DNS:master1,DNS:master2]
export MASTER_NAMES={{cnf["apiserver_names_ssl_aggregator"]}}
export DNS_DOMAIN=cluster.local

[ -z "$SERVICE_CLUSTER_IP_RANGE" ] && { echo "ERROR: Need to set SERVICE_CLUSTER_IP_RANGE"; exit 1; }
[ -z "$MASTER_NAMES" ] && { echo "ERROR: Need to set MASTER_NAMES"; exit 1; }

# Ensure DEST_AGGREGATOR_CERT_DIR is created for auto-generated crt/key
mkdir -p "${DEST_AGGREGATOR_CERT_DIR}" &>/dev/null || sudo mkdir -p "${DEST_AGGREGATOR_CERT_DIR}"
sudo=$(test -w "${DEST_AGGREGATOR_CERT_DIR}" || echo "sudo -E")

# Do generate crt/key, and those files will be copied to DEST_AGGREGATOR_CERT_DIR. 
# 
# In the master node:
# ls /etc/kubernetes/pki/
# ca.crt  ca.key  proxy-client.crt  proxy-client.key
# 
# master_ip_ssl_aggregator is set in GetCertificateProperty(), which will be public IP of first master node.
create-aggregator-certs {{cnf["master_ip_ssl_aggregator"]}}

echo "[SUCCESS] Cert and Key files for aggregator apiserver is generated!"
