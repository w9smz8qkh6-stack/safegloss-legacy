FROM php:8.4.24-apache

RUN apt-get update \
    && apt-get install -y --no-install-recommends libonig-dev \
    && docker-php-ext-install mbstring pdo_mysql \
    && rm -rf /var/lib/apt/lists/* \
    && a2enmod headers rewrite \
    && mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

COPY docker/safegloss.ini "$PHP_INI_DIR/conf.d/safegloss.ini"
COPY public/ /var/www/html/
COPY src/ /var/www/safegloss/src/
COPY bin/ /var/www/safegloss/bin/
COPY tests/ /var/www/safegloss/tests/

RUN chown -R root:root /var/www/html /var/www/safegloss \
    && find /var/www/html /var/www/safegloss -type d -exec chmod 755 {} + \
    && find /var/www/html /var/www/safegloss -type f -exec chmod 644 {} +

USER www-data
