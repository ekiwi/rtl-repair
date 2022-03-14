`timescale 1ns / 1ns
`include "../rtl/inc.v"

module test_f36m_cubic;

    // Inputs
    reg clk;
    reg [`W6:0] a;
    wire [`W6:0] c;

    // Instantiate the Unit Under Test (UUT)
    f36m_cubic uut (
        .clk(clk), 
        .a(a), 
        .c(c)
    );

    initial begin
        // Initialize Inputs
        clk = 0;
        a = 0;

        // Wait 100 ns for global reset to finish
        #100;
        
        // Add stimulus here
        a = {{194'h225016412804a89a862aa1865268898886919259910155856,194'h10258285148a0048861944a264aa161a048829812a1961218},{194'ha9a29a12069660862a6a651806416061940925809115510a,194'h4115a2024962a809a065428aa6088668249a2890a5518a69},{194'h12918199902558a859412a9596148a00520685401210a95a8,194'h1505090561625145816a11225085092955995885598049126}};
        #100;
        if(c !== {{194'ha9926611a84a4114aa562246626418486540006a4829a014,194'h8644a469852659949412582a1a262145524206028042690a},{194'h2585255021628414524615aa156881a642605a0a446018622,194'haaa8806216a0555a04194a2110464440a2964246a56a1020},{194'h14092128882119a9a050a6149146a21810891996014002449,194'h14980a940a502a4821852486460690605815894849aa20a08}})
            $display("E");
        $finish;
    end
    
    always #5 clk = ~clk;
endmodule

