/*

Copyright (c) 2016-2018 Alex Forencich

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
 * Testbench for axis_switch
 */
module test_axis_switch_4x1(input clk, output reg genclock);

// Parameters
parameter S_COUNT = 4;
parameter M_COUNT = 1;
parameter DATA_WIDTH = 8;
parameter KEEP_ENABLE = (DATA_WIDTH>8);
parameter KEEP_WIDTH = (DATA_WIDTH/8);
parameter ID_ENABLE = 1;
parameter ID_WIDTH = 8;
parameter DEST_WIDTH = $clog2(M_COUNT+1);
parameter USER_ENABLE = 1;
parameter USER_WIDTH = 1;
parameter M_BASE = 0;
parameter M_TOP = {3'd3, 3'd2, 3'd1, 3'd0};
parameter M_CONNECT = {M_COUNT{{S_COUNT{1'b1}}}};
parameter S_REG_TYPE = 0;
parameter M_REG_TYPE = 2;
parameter ARB_TYPE_ROUND_ROBIN = 1;
parameter ARB_LSB_HIGH_PRIORITY = 1;

// Inputs

reg rst /*verilator public*/ = 0;
reg [7:0] current_test = 0;

reg [31:0] cycle = 0;

reg [S_COUNT*DATA_WIDTH-1:0] s_axis_tdata /*verilator public*/ = 0;
reg [S_COUNT*KEEP_WIDTH-1:0] s_axis_tkeep /*verilator public*/ = 0;
reg [S_COUNT-1:0] s_axis_tvalid /*verilator public*/ = 0;
reg [S_COUNT-1:0] s_axis_tlast /*verilator public*/ = 0;
reg [S_COUNT*ID_WIDTH-1:0] s_axis_tid /*verilator public*/ = 0;
reg [S_COUNT*DEST_WIDTH-1:0] s_axis_tdest /*verilator public*/ = 0;
reg [S_COUNT*USER_WIDTH-1:0] s_axis_tuser /*verilator public*/ = 0;
reg [M_COUNT-1:0] m_axis_tready /*verilator public*/ = 0;

// Outputs
wire [S_COUNT-1:0] s_axis_tready /*verilator public*/;
wire [M_COUNT*DATA_WIDTH-1:0] m_axis_tdata /*verilator public*/;
wire [M_COUNT*KEEP_WIDTH-1:0] m_axis_tkeep /*verilator public*/;
wire [M_COUNT-1:0] m_axis_tvalid /*verilator public*/;
wire [M_COUNT-1:0] m_axis_tlast /*verilator public*/;
wire [M_COUNT*ID_WIDTH-1:0] m_axis_tid /*verilator public*/;
wire [M_COUNT*DEST_WIDTH-1:0] m_axis_tdest /*verilator public*/;
wire [M_COUNT*USER_WIDTH-1:0] m_axis_tuser /*verilator public*/;

initial begin
    // myhdl integration
    $display("@@@Bug: Misindexing occurs at line 228 and 296!");
    rst = 1;

end

always @(posedge clk) begin
        genclock <= cycle < 12;
        cycle <= cycle + 1;

        if(cycle == 0) begin
            rst <= 0;
            s_axis_tdata <= 32'habcd1234;
            s_axis_tkeep <= 4'b1111;
            s_axis_tvalid <= 4'b1111;
            s_axis_tlast <= 0;
            s_axis_tid <= 32'h01020304;
            s_axis_tdest <= 4'b1101;
            s_axis_tuser <= 0;
            m_axis_tready <= 1'b1;
        end
        else if (cycle == 1) begin
            s_axis_tvalid <= 4'b1111;
            s_axis_tlast <= 4'b1000;
        end
        else if (cycle == 2) begin
            s_axis_tvalid <= 4'b0111;
            s_axis_tlast <= 4'b0100;
        end
        else if (cycle == 3) begin
            s_axis_tvalid <= 4'b0011;
            s_axis_tlast <= 4'b0010;
        end
        else if (cycle == 4) begin
            s_axis_tdata <= 32'habcd1234;
            s_axis_tkeep <= 4'b1111;
            s_axis_tvalid <= 4'b0001;
            s_axis_tlast <= 4'b0001;
            s_axis_tid <= 32'h01020304;
            s_axis_tdest <= 0;
            s_axis_tuser <= 0;
            m_axis_tready <= 1'b1;
        end
        else if (cycle == 5) begin
            s_axis_tvalid <= 4'b0000;
        end
        else if (cycle == 6) begin
            
        end
        else if (cycle == 7) begin
            
        end
        else if (cycle == 8) begin
            
        end
        else if (cycle == 12) begin
            $finish;
        end
    end

always @(*) begin
    if(cycle == 5) begin
        if (!m_axis_tvalid && m_axis_tlast) begin  //output data should be 0xcd 0xab 0xcd 0xab 0xcd, with tlast==1 at the last 0xcd
            $display("@@@Error: The data from input is not outputed!");
        end
    end
end


axis_switch
/* disabled to test default parameterization which should match
#(
    .M_COUNT(M_COUNT),
    .S_COUNT(S_COUNT),
    .DATA_WIDTH(DATA_WIDTH),
    .KEEP_ENABLE(KEEP_ENABLE),
    .KEEP_WIDTH(KEEP_WIDTH),
    .ID_ENABLE(ID_ENABLE),
    .ID_WIDTH(ID_WIDTH),
    .DEST_WIDTH(DEST_WIDTH),
    .USER_ENABLE(USER_ENABLE),
    .USER_WIDTH(USER_WIDTH),
    .M_BASE(M_BASE),
    .M_TOP(M_TOP),
    .M_CONNECT(M_CONNECT),
    .S_REG_TYPE(S_REG_TYPE),
    .M_REG_TYPE(M_REG_TYPE),
    .ARB_TYPE("ROUND_ROBIN"),
    .LSB_PRIORITY("HIGH")
)
*/
UUT (
    .clk(clk),
    .rst(rst),
    // AXI inputs
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tid(s_axis_tid),
    .s_axis_tdest(s_axis_tdest),
    .s_axis_tuser(s_axis_tuser),
    // AXI output
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tid(m_axis_tid),
    .m_axis_tdest(m_axis_tdest),
    .m_axis_tuser(m_axis_tuser)
);

endmodule
