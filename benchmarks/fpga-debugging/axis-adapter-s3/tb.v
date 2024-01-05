/*

Copyright (c) 2014 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

// Language: Verilog 2001

`timescale 1ns / 1ps

module test_axis_adapter_64_8();

reg genclock;
reg clk;

initial begin
    clk = 0;
    forever begin
        #1 clk = ~clk; 
    end
end

// parameters
localparam INPUT_DATA_WIDTH = 64;
localparam INPUT_KEEP_WIDTH = (INPUT_DATA_WIDTH/8);
localparam OUTPUT_DATA_WIDTH = 8;
localparam OUTPUT_KEEP_WIDTH = (OUTPUT_DATA_WIDTH/8);

// Inputs
reg [31:0] cycle = 0;
reg rst = 1;
reg [7:0] current_test = 0;

reg [INPUT_DATA_WIDTH-1:0] input_axis_tdata = 0;
reg [INPUT_KEEP_WIDTH-1:0] input_axis_tkeep = 0;
reg input_axis_tvalid = 0;
reg input_axis_tlast = 0;
reg input_axis_tuser = 0;
reg output_axis_tready = 0;

// Outputs
wire input_axis_tready;
wire [OUTPUT_DATA_WIDTH-1:0] output_axis_tdata;
wire [OUTPUT_KEEP_WIDTH-1:0] output_axis_tkeep;
wire output_axis_tvalid;
wire output_axis_tlast;
wire output_axis_tuser;

integer f;
// dump I/O
initial begin
  f = $fopen("output.txt");
  $fwrite(f, "rst, input_axis_tdata, input_axis_tkeep, input_axis_tvalid, input_axis_tready, input_axis_tlast, input_axis_tuser, output_axis_tdata, output_axis_tkeep, output_axis_tvalid, output_axis_tready, output_axis_tlast, output_axis_tuser\n");
  forever begin
    @(posedge clk);
    $fwrite(f, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", rst, input_axis_tdata, input_axis_tkeep, input_axis_tvalid, input_axis_tready, input_axis_tlast, input_axis_tuser, output_axis_tdata, output_axis_tkeep, output_axis_tvalid, output_axis_tready, output_axis_tlast, output_axis_tuser);
  end
end

initial begin
    // myhdl integration
    rst = 1'b1;
    input_axis_tdata = 0;
    input_axis_tkeep = 0;
    input_axis_tvalid = 0;
    input_axis_tlast = 0;
    input_axis_tuser = 0;
    output_axis_tready = 0;

end


always @(posedge clk) begin
        genclock <= cycle < 12;
        cycle <= cycle + 1;

        if(cycle == 0) begin
            rst <= 1'b0;
            input_axis_tdata <= 64'habcdabcdabcdabcd;
            input_axis_tkeep <= 8'b00011111;
            input_axis_tvalid <= 1'b0;
            input_axis_tlast <= 0;
            input_axis_tuser <= 0;
            output_axis_tready <= 1'b1;
            
        end
        else if (cycle == 1) begin
        end
        else if(cycle == 2) begin
            input_axis_tvalid <= 1'b1;
            input_axis_tlast <= 1'b1;
        end
        else if(cycle == 3) begin
            input_axis_tvalid <= 1'b0;
            input_axis_tlast <= 1'b0;
        end
        else if(cycle == 4) begin
            
        end
        else if (cycle == 5) begin
            
        end
        else if (cycle == 6) begin
            
        end
        else if(cycle == 7) begin
            
        end
        else if(cycle == 8) begin
            
        end
        else if(cycle == 9) begin
            
        end
        else if (cycle == 10) begin
            
        end
        else if (cycle == 12) begin
            
            $finish;
        end
    end

always @(*) begin
    if(output_axis_tlast&&output_axis_tready&&output_axis_tvalid) begin
        if (output_axis_tdata!=8'hcd) begin  //output data should be 0xcd 0xab 0xcd 0xab 0xcd, with tlast==1 at the last 0xcd
            $display("@@@Error: Output tlast signal rises late!\n Output data should be 0xcd 0xab 0xcd 0xab 0xcd, with tlast==1 at the last 0xcd");
        end
    end
end

`ifdef DUMP_TRACE // used for our OSDD calculations
      initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, UUT);
      end
`endif // DUMP_TRACE


  
      


axis_adapter 
#(
    .INPUT_DATA_WIDTH(INPUT_DATA_WIDTH),
    .INPUT_KEEP_WIDTH(INPUT_KEEP_WIDTH),
    .OUTPUT_DATA_WIDTH(OUTPUT_DATA_WIDTH),
    .OUTPUT_KEEP_WIDTH(OUTPUT_KEEP_WIDTH)
)
UUT (
    .clk(clk),
    .rst(rst),
    // AXI input
    .input_axis_tdata(input_axis_tdata),
    .input_axis_tkeep(input_axis_tkeep),
    .input_axis_tvalid(input_axis_tvalid),
    .input_axis_tready(input_axis_tready),
    .input_axis_tlast(input_axis_tlast),
    .input_axis_tuser(input_axis_tuser),
    // AXI output
    .output_axis_tdata(output_axis_tdata),
    .output_axis_tkeep(output_axis_tkeep),
    .output_axis_tvalid(output_axis_tvalid),
    .output_axis_tready(output_axis_tready),
    .output_axis_tlast(output_axis_tlast),
    .output_axis_tuser(output_axis_tuser)
);

endmodule
