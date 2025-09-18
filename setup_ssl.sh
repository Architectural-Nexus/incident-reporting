#!/bin/bash

# SSL Certificate Setup Script for Incident Reporting System
# This script helps set up SSL certificates for the Apache2 configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check and enable required Apache modules
check_apache_modules() {
    print_info "Checking required Apache modules..."
    
    # Required modules for SSL
    REQUIRED_MODULES="ssl headers expires proxy proxy_http deflate"
    
    for module in $REQUIRED_MODULES; do
        if httpd -M 2>/dev/null | grep -q "${module}_module"; then
            print_info "Module $module is loaded ✓"
        else
            print_warning "Module $module may not be available. Please ensure it's installed and enabled."
        fi
    done
    
    # Check if Apache configuration directory exists
    if [ ! -d "/etc/httpd/conf.d" ]; then
        print_error "Apache configuration directory /etc/httpd/conf.d not found"
        print_error "Please ensure Apache (httpd) is properly installed"
        return 1
    fi
    
    # Check if our configuration file exists
    if [ ! -f "/etc/httpd/conf.d/incident-reports.conf" ]; then
        print_warning "Incident reports Apache configuration not found at /etc/httpd/conf.d/incident-reports.conf"
        print_warning "Please run the deployment script first to create the Apache configuration"
    fi
}

# Function to install certbot for AlmaLinux
install_certbot() {
    print_info "Installing Certbot for Let's Encrypt certificates..."
    
    # Install EPEL repository if not already installed
    dnf install -y epel-release
    
    # Install certbot and Apache plugin
    dnf install -y certbot python3-certbot-apache
    
    print_success "Certbot installed successfully"
}

# Function to setup Let's Encrypt certificate
setup_letsencrypt() {
    local domain=$1
    
    print_info "Setting up Let's Encrypt certificate for domain: $domain"
    
    # Stop Apache temporarily
    systemctl stop httpd 2>/dev/null || true
    
    # Obtain certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@$domain \
        --domains $domain,www.$domain
    
    if [ $? -eq 0 ]; then
        print_success "Let's Encrypt certificate obtained successfully"
        
        # Update Apache configuration with correct certificate paths
        sed -i "s|SSLCertificateFile /etc/ssl/certs/incident-reports.crt|SSLCertificateFile /etc/letsencrypt/live/$domain/fullchain.pem|g" /etc/httpd/conf.d/incident-reports.conf
        sed -i "s|SSLCertificateKeyFile /etc/ssl/private/incident-reports.key|SSLCertificateKeyFile /etc/letsencrypt/live/$domain/privkey.pem|g" /etc/httpd/conf.d/incident-reports.conf
        
        # Setup auto-renewal
        setup_auto_renewal
        
        # Configure SELinux
        configure_selinux_ssl
        
        print_success "Certificate paths updated in Apache configuration"
    else
        print_error "Failed to obtain Let's Encrypt certificate"
        return 1
    fi
}

# Function to setup certificate auto-renewal
setup_auto_renewal() {
    print_info "Setting up automatic certificate renewal..."
    
    # Create renewal hook to reload Apache
    mkdir -p /etc/letsencrypt/renewal-hooks/deploy
    cat > /etc/letsencrypt/renewal-hooks/deploy/httpd-reload.sh << 'EOF'
#!/bin/bash
systemctl reload httpd
EOF
    
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/httpd-reload.sh
    
    # Test auto-renewal
    certbot renew --dry-run
    
    if [ $? -eq 0 ]; then
        print_success "Auto-renewal setup completed successfully"
    else
        print_warning "Auto-renewal test failed, but certificates were installed"
    fi
}

# Function to create self-signed certificate
create_self_signed() {
    local domain=$1
    
    print_info "Creating self-signed certificate for domain: $domain"
    
    # Create SSL directory
    mkdir -p /etc/ssl/certs /etc/ssl/private
    
    # Generate private key
    openssl genrsa -out /etc/ssl/private/incident-reports.key 2048
    
    # Generate certificate
    openssl req -new -x509 -key /etc/ssl/private/incident-reports.key \
        -out /etc/ssl/certs/incident-reports.crt \
        -days 365 \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$domain"
    
    # Set proper permissions
    chmod 600 /etc/ssl/private/incident-reports.key
    chmod 644 /etc/ssl/certs/incident-reports.crt
    
    # Configure SELinux
    configure_selinux_ssl
    
    print_success "Self-signed certificate created successfully"
    print_warning "Self-signed certificates are not trusted by browsers by default"
}

# Function to update Apache configuration with domain
update_apache_domain() {
    local domain=$1
    
    print_info "Updating Apache configuration with domain: $domain"
    
    # Update ServerName in Apache configuration
    sed -i "s/incidents.your-domain.com/$domain/g" /etc/httpd/conf.d/incident-reports.conf
    
    print_success "Apache configuration updated with domain: $domain"
}

# Function to test Apache configuration
test_apache() {
    print_info "Testing Apache configuration..."
    
    httpd -t
    
    if [ $? -eq 0 ]; then
        print_success "Apache configuration is valid"
        return 0
    else
        print_error "Apache configuration has errors"
        return 1
    fi
}

# Function to enable and start Apache
start_apache() {
    print_info "Starting Apache service..."
    
    systemctl enable httpd
    systemctl start httpd
    
    if systemctl is-active --quiet httpd; then
        print_success "Apache service started successfully"
    else
        print_error "Failed to start Apache service"
        return 1
    fi
}

# Function to install enterprise certificate
install_enterprise_cert() {
    local domain=$1
    
    print_info "Setting up enterprise/internal CA certificate for domain: $domain"
    
    echo ""
    echo "📋 Enterprise Certificate Setup Requirements:"
    echo "   - Server certificate file (.crt or .pem)"
    echo "   - Private key file (.key or .pem)"
    echo "   - Certificate chain/bundle file (optional but recommended)"
    echo "   - Root CA certificate (optional, for client trust)"
    echo ""
    
    # Get certificate file path
    while true; do
        read -p "Enter path to your server certificate file: " CERT_PATH
        if [ -f "$CERT_PATH" ]; then
            break
        else
            print_error "Certificate file not found: $CERT_PATH"
        fi
    done
    
    # Get private key file path
    while true; do
        read -p "Enter path to your private key file: " KEY_PATH
        if [ -f "$KEY_PATH" ]; then
            break
        else
            print_error "Private key file not found: $KEY_PATH"
        fi
    done
    
    # Get certificate chain (optional)
    read -p "Enter path to certificate chain/bundle file (press Enter to skip): " CHAIN_PATH
    if [ -n "$CHAIN_PATH" ] && [ ! -f "$CHAIN_PATH" ]; then
        print_warning "Chain file not found: $CHAIN_PATH - continuing without chain"
        CHAIN_PATH=""
    fi
    
    # Get root CA certificate (optional)
    read -p "Enter path to root CA certificate for system trust (press Enter to skip): " CA_PATH
    if [ -n "$CA_PATH" ] && [ ! -f "$CA_PATH" ]; then
        print_warning "CA file not found: $CA_PATH - continuing without CA"
        CA_PATH=""
    fi
    
    # Create SSL directories
    mkdir -p /etc/ssl/certs /etc/ssl/private
    
    # Copy and validate certificate
    print_info "Installing server certificate..."
    cp "$CERT_PATH" /etc/ssl/certs/incident-reports.crt
    chmod 644 /etc/ssl/certs/incident-reports.crt
    
    # Copy and secure private key
    print_info "Installing private key..."
    cp "$KEY_PATH" /etc/ssl/private/incident-reports.key
    chmod 600 /etc/ssl/private/incident-reports.key
    
    # Handle certificate chain
    if [ -n "$CHAIN_PATH" ]; then
        print_info "Installing certificate chain..."
        # Combine server cert and chain into full chain
        cat /etc/ssl/certs/incident-reports.crt "$CHAIN_PATH" > /etc/ssl/certs/incident-reports-fullchain.crt
        chmod 644 /etc/ssl/certs/incident-reports-fullchain.crt
        
        # Update Apache config to use full chain
        sed -i "s|SSLCertificateFile /etc/ssl/certs/incident-reports.crt|SSLCertificateFile /etc/ssl/certs/incident-reports-fullchain.crt|g" /etc/httpd/conf.d/incident-reports.conf
        print_success "Certificate chain installed and Apache updated to use full chain"
    else
        print_warning "No certificate chain provided - browsers may show untrusted warnings"
    fi
    
        # Handle root CA certificate for AlmaLinux
    if [ -n "$CA_PATH" ]; then
        print_info "Installing root CA certificate for system trust..."
        cp "$CA_PATH" /etc/pki/ca-trust/source/anchors/incident-reports-ca.crt
        update-ca-trust
        print_success "Root CA certificate installed in system trust store"
    fi
    
    # Validate certificate and key match
    print_info "Validating certificate and private key..."
    CERT_HASH=$(openssl x509 -noout -modulus -in /etc/ssl/certs/incident-reports.crt | openssl md5)
    KEY_HASH=$(openssl rsa -noout -modulus -in /etc/ssl/private/incident-reports.key | openssl md5)
    
    if [ "$CERT_HASH" = "$KEY_HASH" ]; then
        print_success "Certificate and private key match ✓"
    else
        print_error "Certificate and private key do not match!"
        return 1
    fi
    
    # Display certificate information
    print_info "Certificate Information:"
    openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -subject -issuer -dates
    
    # Configure SELinux
    configure_selinux_ssl
    
    print_success "Enterprise certificate installation completed"
}

# Function to configure SELinux for SSL certificates
configure_selinux_ssl() {
    print_info "Configuring SELinux for SSL certificates..."
    
    if command -v getenforce &> /dev/null && [ "$(getenforce)" != "Disabled" ]; then
        print_info "SELinux is enabled, setting certificate contexts..."
        
        # Set proper SELinux contexts for SSL certificates
        restorecon -R /etc/ssl/certs/ 2>/dev/null || true
        restorecon -R /etc/ssl/private/ 2>/dev/null || true
        restorecon -R /etc/letsencrypt/ 2>/dev/null || true
        
        print_success "SELinux contexts configured for SSL certificates"
    else
        print_info "SELinux is disabled or not available"
    fi
}

# Function to create certificate signing request (CSR)
create_csr() {
    local domain=$1
    
    print_info "Creating Certificate Signing Request (CSR) for domain: $domain"
    
    # Create private key
    print_info "Generating private key..."
    openssl genrsa -out /etc/ssl/private/incident-reports.key 2048
    chmod 600 /etc/ssl/private/incident-reports.key
    
    # Get certificate details
    echo ""
    echo "📋 Certificate Request Information:"
    read -p "Country (2 letter code) [US]: " COUNTRY
    COUNTRY=${COUNTRY:-US}
    
    read -p "State/Province [State]: " STATE
    STATE=${STATE:-State}
    
    read -p "City/Locality [City]: " CITY
    CITY=${CITY:-City}
    
    read -p "Organization [Your Organization]: " ORG
    ORG=${ORG:-Your Organization}
    
    read -p "Organizational Unit [IT Department]: " OU
    OU=${OU:-IT Department}
    
    read -p "Email Address [admin@$domain]: " EMAIL
    EMAIL=${EMAIL:-admin@$domain}
    
    # Create CSR
    print_info "Creating certificate signing request..."
    openssl req -new -key /etc/ssl/private/incident-reports.key \
        -out /etc/ssl/certs/incident-reports.csr \
        -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$domain/emailAddress=$EMAIL"
    
    chmod 644 /etc/ssl/certs/incident-reports.csr
    
    print_success "Certificate Signing Request created successfully"
    print_info "CSR file location: /etc/ssl/certs/incident-reports.csr"
    
    echo ""
    echo "📋 Next Steps:"
    echo "1. Submit the CSR file to your Certificate Authority"
    echo "2. Download the signed certificate from your CA"
    echo "3. Run this script again and select option 2 to install the signed certificate"
    echo ""
    echo "CSR Content (submit this to your CA):"
    echo "========================================="
    cat /etc/ssl/certs/incident-reports.csr
    echo "========================================="
}

# Main menu
show_menu() {
    echo ""
    echo "======================================================="
    echo "🔒 SSL Certificate Setup for Incident Reporting System"
    echo "======================================================="
    echo ""
    echo "1. Setup Let's Encrypt certificate (public internet)"
    echo "2. Install enterprise/internal CA certificate"
    echo "3. Create Certificate Signing Request (CSR) for CA"
    echo "4. Create self-signed certificate (testing only)"
    echo "5. Update domain in Apache configuration only"
    echo "6. Test Apache configuration"
    echo "7. View current certificate information"
    echo "8. Exit"
    echo ""
}

# Function to view current certificate information
view_certificate_info() {
    print_info "Current SSL Certificate Information"
    
    if [ -f "/etc/ssl/certs/incident-reports.crt" ]; then
        echo ""
        echo "📋 Certificate Details:"
        openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -text | grep -A2 "Subject:"
        openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -text | grep -A2 "Issuer:"
        openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -dates
        
        echo ""
        echo "📋 Certificate Validity:"
        openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -checkend 0 && \
            print_success "Certificate is currently valid" || \
            print_error "Certificate has expired or is not yet valid"
        
        # Check if certificate expires within 30 days
        if openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -checkend 2592000; then
            print_success "Certificate is valid for more than 30 days"
        else
            print_warning "Certificate expires within 30 days"
        fi
        
        echo ""
        echo "📋 Certificate Files:"
        echo "   Certificate: /etc/ssl/certs/incident-reports.crt"
        [ -f "/etc/ssl/certs/incident-reports-fullchain.crt" ] && echo "   Full Chain: /etc/ssl/certs/incident-reports-fullchain.crt"
        echo "   Private Key: /etc/ssl/private/incident-reports.key"
        [ -f "/etc/ssl/certs/incident-reports.csr" ] && echo "   CSR: /etc/ssl/certs/incident-reports.csr"
        
    elif [ -f "/etc/letsencrypt/live/*/fullchain.pem" ]; then
        local cert_path=$(find /etc/letsencrypt/live -name "fullchain.pem" | head -1)
        print_info "Let's Encrypt certificate found: $cert_path"
        openssl x509 -in "$cert_path" -noout -subject -issuer -dates
    else
        print_warning "No SSL certificates found"
    fi
}

# Main execution
main() {
    check_root
    check_apache_modules
    
    # Get domain name for most operations
    echo "Enter your domain name (e.g., incident-reports.yourcompany.com):"
    read -r DOMAIN
    
    if [ -z "$DOMAIN" ]; then
        print_error "Domain name is required"
        exit 1
    fi
    
    while true; do
        show_menu
        read -p "Select an option (1-8): " choice
        
        case $choice in
            1)
                install_certbot
                update_apache_domain "$DOMAIN"
                setup_letsencrypt "$DOMAIN"
                if test_apache; then
                    start_apache
                    print_success "SSL setup completed! Your site should be available at https://$DOMAIN"
                fi
                break
                ;;
            2)
                update_apache_domain "$DOMAIN"
                install_enterprise_cert "$DOMAIN"
                if test_apache; then
                    start_apache
                    print_success "Enterprise SSL setup completed! Your site should be available at https://$DOMAIN"
                fi
                break
                ;;
            3)
                update_apache_domain "$DOMAIN"
                create_csr "$DOMAIN"
                print_info "CSR created. Install the signed certificate using option 2 when ready."
                break
                ;;
            4)
                update_apache_domain "$DOMAIN"
                create_self_signed "$DOMAIN"
                if test_apache; then
                    start_apache
                    print_success "Self-signed SSL setup completed! Your site should be available at https://$DOMAIN"
                    print_warning "Remember to accept the certificate warning in your browser"
                fi
                break
                ;;
            5)
                update_apache_domain "$DOMAIN"
                print_success "Domain updated in Apache configuration"
                print_info "You still need to setup SSL certificates manually"
                break
                ;;
            6)
                test_apache
                break
                ;;
            7)
                view_certificate_info
                break
                ;;
            8)
                print_info "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid option. Please select 1-8."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue or Ctrl+C to exit..."
    done
}

# Run main function
main "$@"
