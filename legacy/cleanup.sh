DOWNLOADS_DIR=$1
DATA_DIR=$2

echo "Deleting from $DOWNLOADS_DIR"
find $DOWNLOADS_DIR -mtime +5 -exec echo -n "Deleting " \; -print -delete

echo "Deleting from $DATA_DIR"
find $DATA_DIR -mtime +5 -exec echo -n "Deleting " \; -print -delete
