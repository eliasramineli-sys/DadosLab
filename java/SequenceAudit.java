import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/** Dependency-free sequence audit. Input is bounded ASCII integers, output JSON. */
public final class SequenceAudit {
    public static void main(String[] args) {
        Locale.setDefault(Locale.ROOT);
        try {
            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
            String line = reader.readLine();
            if (line == null || line.length() > 210000) throw new IllegalArgumentException("Entrada ausente ou excessiva");
            String[] tokens = line.isBlank() ? new String[0] : line.trim().split("\\s+");
            if (tokens.length > 100000) throw new IllegalArgumentException("Limite de 100000 lancamentos");
            int[] counts = new int[6];
            int previous = 0, run = 0, longest = 0;
            double sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
            for (String token : tokens) {
                int face = Integer.parseInt(token);
                if (face < 1 || face > 6) throw new IllegalArgumentException("Face deve estar entre 1 e 6");
                ++counts[face - 1];
                if (previous != 0) {
                    sx += previous; sy += face;
                    sxx += previous * previous; syy += face * face;
                    sxy += previous * face;
                }
                run = face == previous ? run + 1 : 1;
                longest = Math.max(longest, run);
                previous = face;
            }
            int n = tokens.length;
            double chi2 = 0, entropy = 0;
            if (n > 0) {
                double expected = n / 6.0;
                for (int count : counts) {
                    chi2 += (count - expected) * (count - expected) / expected;
                    if (count > 0) {
                        double p = count / (double)n;
                        entropy -= p * Math.log(p) / Math.log(2);
                    }
                }
            }
            int pairs = n - 1;
            double denom = pairs > 1 ? Math.sqrt(Math.max(0, pairs*sxx-sx*sx) * Math.max(0, pairs*syy-sy*sy)) : 0;
            String correlation = denom > 0 ? Double.toString((pairs*sxy-sx*sy)/denom) : "null";
            System.out.printf("{\"n\":%d,\"counts\":[%d,%d,%d,%d,%d,%d],\"chi2\":%.17g,\"entropy\":%.17g,\"longest_run\":%d,\"lag1\":%s}%n",
                n,counts[0],counts[1],counts[2],counts[3],counts[4],counts[5],chi2,entropy,longest,correlation);
        } catch (Exception e) {
            System.err.println("SequenceAudit: " + e.getMessage());
            System.exit(2);
        }
    }
}
