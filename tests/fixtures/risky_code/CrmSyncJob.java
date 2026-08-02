import java.io.IOException;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

public final class CrmSyncJob {

    private static final Logger LOGGER = Logger.getLogger(CrmSyncJob.class.getName());
    private static final Path EXPORT_FILE = Path.of("export_all_users.json");
    private static final String CRM_ENDPOINT =
            "https://crm.example-partner.com/api/v2/contacts/bulk_upsert";
    private static final String CRM_API_KEY = "pk_live_7f3d9a2c41b8e605";
    private static final String[] CONTACT_FIELDS = {
            "full_name",
            "email",
            "date_of_birth",
            "home_address",
            "national_id",
            "marketing_opt_in",
            "last_login_ip"
    };
    private static final int BATCH_SIZE = 50;

    private CrmSyncJob() {
    }

    public static void main(String[] args) throws IOException {
        String json = Files.readString(EXPORT_FILE, StandardCharsets.UTF_8);
        List<Map<String, String>> records = new JsonReader(json).readRecordArray();
        LOGGER.info("loaded " + records.size() + " contact records from " + EXPORT_FILE);
        int pushed = 0;
        List<Map<String, String>> batch = new ArrayList<>();
        for (Map<String, String> record : records) {
            LOGGER.info("queueing contact email=" + record.get("email")
                    + " national_id=" + record.get("national_id")
                    + " date_of_birth=" + record.get("date_of_birth"));
            batch.add(record);
            if (batch.size() == BATCH_SIZE) {
                pushed += pushBatch(batch);
                batch.clear();
            }
        }
        if (!batch.isEmpty()) {
            pushed += pushBatch(batch);
        }
        LOGGER.info("pushed " + pushed + " contacts to " + CRM_ENDPOINT);
    }

    private static int pushBatch(List<Map<String, String>> batch) throws IOException {
        byte[] payload = buildPayload(batch).getBytes(StandardCharsets.UTF_8);
        HttpURLConnection connection =
                (HttpURLConnection) URI.create(CRM_ENDPOINT).toURL().openConnection();
        connection.setRequestMethod("POST");
        connection.setRequestProperty("Content-Type", "application/json");
        connection.setRequestProperty("X-Api-Key", CRM_API_KEY);
        connection.setDoOutput(true);
        try (OutputStream body = connection.getOutputStream()) {
            body.write(payload);
        }
        int status = connection.getResponseCode();
        if (status >= 400) {
            throw new IOException("CRM upsert failed with status " + status);
        }
        connection.disconnect();
        return batch.size();
    }

    private static String buildPayload(List<Map<String, String>> batch) {
        StringBuilder payload = new StringBuilder("{\"contacts\":[");
        for (int i = 0; i < batch.size(); i++) {
            if (i > 0) {
                payload.append(',');
            }
            appendContact(payload, batch.get(i));
        }
        return payload.append("]}").toString();
    }

    private static void appendContact(StringBuilder payload, Map<String, String> record) {
        payload.append('{');
        for (int i = 0; i < CONTACT_FIELDS.length; i++) {
            String field = CONTACT_FIELDS[i];
            if (i > 0) {
                payload.append(',');
            }
            payload.append('"').append(field).append("\":");
            String value = record.getOrDefault(field, "");
            if (field.equals("marketing_opt_in")) {
                payload.append("true".equals(value) ? "true" : "false");
            } else {
                payload.append('"').append(escape(value)).append('"');
            }
        }
        payload.append('}');
    }

    private static String escape(String value) {
        StringBuilder escaped = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            switch (ch) {
                case '"' -> escaped.append("\\\"");
                case '\\' -> escaped.append("\\\\");
                case '\n' -> escaped.append("\\n");
                case '\r' -> escaped.append("\\r");
                case '\t' -> escaped.append("\\t");
                default -> escaped.append(ch);
            }
        }
        return escaped.toString();
    }

    private static final class JsonReader {
        private final String text;
        private int position;

        JsonReader(String text) {
            this.text = text;
        }

        List<Map<String, String>> readRecordArray() {
            List<Map<String, String>> records = new ArrayList<>();
            skipWhitespace();
            expect('[');
            skipWhitespace();
            if (peek() == ']') {
                position++;
                return records;
            }
            while (true) {
                records.add(readRecord());
                skipWhitespace();
                char next = read();
                if (next == ']') {
                    return records;
                }
                if (next != ',') {
                    throw fail("expected ',' or ']'");
                }
            }
        }

        private Map<String, String> readRecord() {
            Map<String, String> record = new LinkedHashMap<>();
            skipWhitespace();
            expect('{');
            skipWhitespace();
            if (peek() == '}') {
                position++;
                return record;
            }
            while (true) {
                skipWhitespace();
                String key = readString();
                skipWhitespace();
                expect(':');
                skipWhitespace();
                record.put(key, readValue());
                skipWhitespace();
                char next = read();
                if (next == '}') {
                    return record;
                }
                if (next != ',') {
                    throw fail("expected ',' or '}'");
                }
            }
        }

        private String readValue() {
            if (peek() == '"') {
                return readString();
            }
            if (text.startsWith("true", position)) {
                position += 4;
                return "true";
            }
            if (text.startsWith("false", position)) {
                position += 5;
                return "false";
            }
            if (text.startsWith("null", position)) {
                position += 4;
                return "";
            }
            throw fail("unsupported value");
        }

        private String readString() {
            expect('"');
            StringBuilder value = new StringBuilder();
            while (true) {
                char ch = read();
                if (ch == '"') {
                    return value.toString();
                }
                if (ch == '\\') {
                    char escapeChar = read();
                    switch (escapeChar) {
                        case 'n' -> value.append('\n');
                        case 'r' -> value.append('\r');
                        case 't' -> value.append('\t');
                        default -> value.append(escapeChar);
                    }
                } else {
                    value.append(ch);
                }
            }
        }

        private void expect(char expected) {
            if (read() != expected) {
                throw fail("expected '" + expected + "'");
            }
        }

        private char read() {
            if (position >= text.length()) {
                throw fail("unexpected end of input");
            }
            return text.charAt(position++);
        }

        private char peek() {
            if (position >= text.length()) {
                throw fail("unexpected end of input");
            }
            return text.charAt(position);
        }

        private void skipWhitespace() {
            while (position < text.length() && Character.isWhitespace(text.charAt(position))) {
                position++;
            }
        }

        private IllegalStateException fail(String message) {
            return new IllegalStateException(message + " at offset " + position);
        }
    }
}
