<?php
require 'config/database.php';
$stmt = $connection->query("SELECT 1");
if ($stmt) {
    echo "PHP MySQL connection test successful.";
} else {
    echo "PHP MySQL connection test failed.";
}
?>
