import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Stack;

import org.xml.sax.SAXException;

import de.l3s.boilerpipe.BoilerpipeProcessingException;
import de.l3s.boilerpipe.extractors.*;

public class ExtractTextFromHTMLFiles {

    public static void main(String[] args) throws BoilerpipeProcessingException, IOException, SAXException {

        String input_filelist_filename = args[0]; // file containing a list of filenames

        Stack<String> filestack = new Stack<>();

        BufferedReader filelistreader = new BufferedReader(new FileReader(input_filelist_filename));

        String text;

        String input_filename;
        String output_filename;

        while (filelistreader.ready()) {
            text = filelistreader.readLine();
            filestack.push(text);
        }

        filelistreader.close();

        while (!filestack.isEmpty()) {
            input_filename = filestack.pop();

            BufferedReader reader = new BufferedReader(new FileReader(input_filename));

            StringBuffer htmlBuffer = new StringBuffer();
    
            while (reader.ready()) {
                htmlBuffer.append(reader.readLine() + "\n");
            }

            reader.close();

            text = KeepEverythingExtractor.INSTANCE.getText(htmlBuffer.toString());

            output_filename = input_filename + ".txt";

            BufferedWriter writer = new BufferedWriter(new FileWriter(output_filename));

            writer.write(text);
            writer.close();

        }

    }
}
