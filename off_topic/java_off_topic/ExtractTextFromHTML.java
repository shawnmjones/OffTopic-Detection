import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;

import org.xml.sax.SAXException;

import de.l3s.boilerpipe.BoilerpipeProcessingException;
import de.l3s.boilerpipe.extractors.*;

public class ExtractTextFromHTML {

    public static void main(String[] args) throws BoilerpipeProcessingException, IOException, SAXException {

        String input_filename = args[0];
        String output_filename = args[1];
        String text = "";

        BufferedReader reader = new BufferedReader(new FileReader(input_filename));

        StringBuffer htmlBuffer = new StringBuffer();

        while (reader.ready()) {
            htmlBuffer.append(reader.readLine() + "\n");
        }

        reader.close();

        text = KeepEverythingExtractor.INSTANCE.getText(htmlBuffer.toString());

        BufferedWriter writer = new BufferedWriter(new FileWriter(output_filename));

        writer.write(text);
        writer.close();

    }
}
