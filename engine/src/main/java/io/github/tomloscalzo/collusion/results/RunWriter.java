package io.github.tomloscalzo.collusion.results;

import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** JSONL output: one run per line, sorted keys, UTF-8, LF line ends. */
public final class RunWriter {
    private RunWriter() {}

    public static String line(RunRecord r) {
        return Canonical.text(r.toJson());
    }

    public static void append(Path file, RunRecord r) throws IOException {
        try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8, StandardOpenOption.CREATE,
                StandardOpenOption.APPEND)) {
            w.write(line(r));
            w.write('\n');
        }
    }
}
