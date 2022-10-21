DOWNLOADS_DIR=$1
DATA_DIR=$2
DELETE_BEFORE_DAYS=$3

echo "----------Deleting from $DOWNLOADS_DIR > $DELETE_BEFORE_DAYS days old----------"
find $DOWNLOADS_DIR -mtime +$DELETE_BEFORE_DAYS -exec echo -n "Deleting " \; -print -delete

echo ""

echo "----------Deleting from $DATA_DIR > $DELETE_BEFORE_DAYS days old--------------"
find $DATA_DIR -mtime +$DELETE_BEFORE_DAYS -exec echo -n "Deleting " \; -print -delete
