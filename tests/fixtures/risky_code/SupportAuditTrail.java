import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.time.Instant;
import java.util.Set;
import java.util.stream.Stream;

public final class SupportAuditTrail {

    private static final Path AUDIT_LOG = Path.of("support_audit.log");
    private static final Set<PosixFilePermission> WORLD_READABLE =
            PosixFilePermissions.fromString("rw-rw-rw-");

    private final Path logFile;

    public SupportAuditTrail() {
        this(AUDIT_LOG);
    }

    public SupportAuditTrail(Path logFile) {
        this.logFile = logFile;
    }

    public void recordTicket(String ticketId, String email, String nationalId, String summary)
            throws IOException {
        String line = Instant.now() + " ticket=" + ticketId
                + " email=" + email
                + " national_id=" + nationalId
                + " summary=" + summary.replace('\n', ' ')
                + System.lineSeparator();
        Files.writeString(logFile, line, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        Files.setPosixFilePermissions(logFile, WORLD_READABLE);
    }

    public long countEntries() throws IOException {
        try (Stream<String> lines = Files.lines(logFile, StandardCharsets.UTF_8)) {
            return lines.count();
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length < 4) {
            System.err.println("usage: SupportAuditTrail <ticketId> <email> <nationalId> <summary>");
            System.exit(1);
        }
        SupportAuditTrail trail = new SupportAuditTrail();
        trail.recordTicket(args[0], args[1], args[2], args[3]);
        System.out.println("audit entries on file: " + trail.countEntries());
    }
}
