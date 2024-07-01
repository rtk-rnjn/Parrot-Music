if ! command -v java &> /dev/null; then
    echo "Java is not installed. Please install Java 11 or higher."
    exit 1
fi

if [ ! -f lavalink/Lavalink.jar ]; then
    echo "Lavalink.jar not found."
    exit 1
fi

java -jar lavalink/Lavalink.jar
