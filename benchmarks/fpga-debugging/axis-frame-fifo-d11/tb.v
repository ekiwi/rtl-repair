/*

Copyright (c) 2014-2018 Alex Forencich

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

/*
 * Testbench for axis_fifo
 */
module test_axis_fifo();

reg genclock;
reg clk;

initial begin
    clk = 0;
    forever begin
        #1 clk = ~clk; 
    end
end

// Parameters
parameter DEPTH = 4;
parameter DATA_WIDTH = 8;
parameter KEEP_ENABLE = (DATA_WIDTH>8);
parameter KEEP_WIDTH = (DATA_WIDTH/8);
parameter LAST_ENABLE = 1;
parameter ID_ENABLE = 1;
parameter ID_WIDTH = 8;
parameter DEST_ENABLE = 1;
parameter DEST_WIDTH = 8;
parameter USER_ENABLE = 1;
parameter USER_WIDTH = 1;
parameter FRAME_FIFO = 1;
parameter USER_BAD_FRAME_VALUE = 1'b1;
parameter USER_BAD_FRAME_MASK = 1'b1;
parameter DROP_BAD_FRAME = 0;
parameter DROP_WHEN_FULL = 1;

// Inputs
reg [31:0] cycle = 0;

reg rst = 0;
reg [7:0] current_test = 0;

reg [DATA_WIDTH-1:0] s_axis_tdata = 0;
reg s_axis_tvalid = 0;
reg s_axis_tlast = 0;
reg s_axis_tuser = 0;
reg m_axis_tready = 0;

// Outputs
wire s_axis_tready;
wire [DATA_WIDTH-1:0] m_axis_tdata;
wire m_axis_tvalid;
wire m_axis_tlast;
wire drop_frame;


integer f;
// dump I/O
initial begin
  f = $fopen("output.txt");
  $fwrite(f, "rst, s_axis_tdata, s_axis_tvalid, s_axis_tready, s_axis_tlast, s_axis_tuser, m_axis_tdata, m_axis_tvalid, m_axis_tready, m_axis_tlast, drop_frame\n");
  forever begin
    @(posedge clk);
    $fwrite(f, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",rst, s_axis_tdata, s_axis_tvalid, s_axis_tready, s_axis_tlast, s_axis_tuser, m_axis_tdata, m_axis_tvalid, m_axis_tready, m_axis_tlast, drop_frame);
  end
end

initial begin
    // myhdl integration
    rst = 1'b1;
    s_axis_tdata = 1;
    s_axis_tvalid = 1'b1;
    s_axis_tlast = 0;
    s_axis_tuser = 0;
    m_axis_tready = 0;

end


always @(posedge clk) begin
        genclock <= cycle < 12;
        cycle <= cycle + 1;

        if(cycle == 0) begin
            rst <= 1'b0;
            s_axis_tdata <= 1;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= 1;
            s_axis_tuser <= 0;
            m_axis_tready <= 1;
            
        end
        else if (cycle == 1) begin
           s_axis_tdata <= 1;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= 1;
            s_axis_tuser <= 0;
            m_axis_tready <= 0;
        end
        else if(cycle == 2) begin
            s_axis_tdata <= 2;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= 1;
            s_axis_tuser <= 0;
            m_axis_tready <= 0;
        end
        else if(cycle == 3) begin
            s_axis_tdata <= 4;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= 1;
            s_axis_tuser <= 0;
            m_axis_tready <= 0;
        end
        else if (cycle == 4) begin
            s_axis_tdata <= 5;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= 0;
            s_axis_tuser <= 0;
            m_axis_tready <= 0;
        end
        else if (cycle == 5) begin
            s_axis_tdata <= 6;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= 0;
            s_axis_tuser <= 0;
            m_axis_tready <= 0;
        end
        else if(cycle == 11) begin
            rst <= 1'b1;
        end
        else if(cycle == 12) begin
            rst <= 1'b0;
        end
        else if(cycle == 13) begin
            s_axis_tlast <= 1'b1;
        end
        else if (cycle == 14) begin
            s_axis_tlast <= 1'b0;
            s_axis_tdata <= 7;
        end
        else if (cycle == 16) begin
            $finish;
        end
    end

always @(*) begin
    if(cycle==13&&drop_frame!=0) begin
        $display("@@@Error: Failed to reset drop_frame!");
        $finish;
    end
end


axis_frame_fifo 
/*
#(
    .ADDR_WIDTH(2),
    .DATA_WIDTH(DATA_WIDTH),
    .DROP_WHEN_FULL(DROP_WHEN_FULL)
)
*/
UUT (
    .clk(clk),
    .rst(rst),
    // AXI input
    .input_axis_tdata(s_axis_tdata),
    .input_axis_tvalid(s_axis_tvalid),
    .input_axis_tready(s_axis_tready),
    .input_axis_tlast(s_axis_tlast),
    .input_axis_tuser(s_axis_tuser),
    // AXI output
    .output_axis_tdata(m_axis_tdata),
    .output_axis_tvalid(m_axis_tvalid),
    .output_axis_tready(m_axis_tready),
    .output_axis_tlast(m_axis_tlast),
    .drop_frame(drop_frame)
);

`ifdef DUMP_TRACE // used for our OSDD calculations
initial begin
  $dumpfile("dump.vcd");
  $dumpvars(0, UUT);
end
`endif // DUMP_TRACE

endmodule
