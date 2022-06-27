/**
 * Testbench for sdram_controller modules, simulates:
 *  - Iinit
 *  - Write
 *  - Read
 */
module sdram_controller_tb();

    /*vlog_tb_utils vlog_tb_utils0();*/

    /* HOST CONTROLLS */
    reg [23:0]  haddr;
    reg [15:0]  data_input;
    wire [15:0] data_output;
    reg [23:0]  rd_addr = 'dx; // read address was never defined in tb...
    wire busy; 
    reg rd_enable, wr_enable, rst_n, clk;
    reg instrumented_clk;

    /* SDRAM SIDE */
    wire [12:0] addr;
    wire [1:0] bank_addr;
    wire [15:0] data; 
    wire clock_enable, cs_n, ras_n, cas_n, we_n, rd_ready, data_mask_low, data_mask_high;

    reg [15:0] data_r;

    assign data = data_r;


    initial 
    begin
        haddr = 24'd0;
        data_input = 16'd0;
        rd_enable = 1'b0;
        wr_enable = 1'b0;
        rst_n = 1'b1;
        clk = 1'b0;
        instrumented_clk=1'b0;
        data_r = 16'hzzzz;
    end

    always
        #1 clk <= ~clk;
    
    always #4 instrumented_clk=~instrumented_clk;
    
    integer f;

    initial begin
        f = $fopen("output_sdram_controller_tb_t1.txt");
        // inputs
        $fwrite(f, "time,wr_addr,wr_data,wr_enable,rd_addr,rd_enable,rst_n,clk,");
        // outputs
        $fwrite(f, "rd_data,rd_ready,busy,addr,bank_addr,data,clock_enable,cs_n,ras_n,cas_n,we_n,data_mask_low,data_mask_high\n");
	forever begin
	    @(posedge clk);
        // inputs
        $fwrite(f,"%g,%d,%d,%d,%d,%d,%d,%d,", $time, haddr,data_input,wr_enable,rd_addr,rd_enable,rst_n,clk);
        // outputs
        $fwrite(f,"%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", data_output,rd_ready,busy,addr,bank_addr,data,clock_enable,cs_n,ras_n,cas_n,we_n,data_mask_low,data_mask_high);
	end
    end

    initial
    begin
        $dumpfile("dump.vcd");
        $dumpvars(0, sdram_controlleri);
    end

    initial
    begin
      #3 rst_n = 1'b0;
      #3 rst_n = 1'b1;
      
      #120 haddr = 24'hfedbed;
      data_input = 16'd3333;
      
      #3 wr_enable = 1'b1;
      #6 wr_enable = 1'b0;
      haddr = 24'd0;
      data_input = 16'd0;  
      
      #120 haddr = 24'hbedfed;
      #3 rd_enable = 1'b1;
      #6 rd_enable = 1'b0;
      haddr = 24'd0;
      
      #8 data_r = 16'hbbbb;
      #2 data_r = 16'hzzzz;
      
      #1000
      $fclose(f);
      $finish;
    end


sdram_controller sdram_controlleri (
    /* HOST INTERFACE */
    .wr_addr(haddr), 
    .wr_data(data_input),
    .rd_data(data_output), .rd_ready(rd_ready), .rd_addr(rd_addr),
    .busy(busy), .rd_enable(rd_enable), .wr_enable(wr_enable), .rst_n(rst_n), .clk(clk),

    /* SDRAM SIDE */
    .addr(addr), .bank_addr(bank_addr), .data(data), .clock_enable(clock_enable), .cs_n(cs_n), .ras_n(ras_n), .cas_n(cas_n), .we_n(we_n), .data_mask_low(data_mask_low), .data_mask_high(data_mask_high)
);

endmodule
