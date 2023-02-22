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
        $fwrite(f, "time,rd_data[15],rd_data[14],rd_data[13],rd_data[12],rd_data[11],rd_data[10],rd_data[9],rd_data[8],rd_data[7],rd_data[6],rd_data[5],rd_data[4],rd_data[3],rd_data[2],rd_data[1],rd_data[0],rd_ready,addr[12],addr[11],addr[10],addr[9],addr[8],addr[7],addr[6],addr[5],addr[4],addr[3],addr[2],addr[1],addr[0],bank_addr[1],bank_addr[0],data[15],data[14],data[13],data[12],data[11],data[10],data[9],data[8],data[7],data[6],data[5],data[4],data[3],data[2],data[1],data[0],clock_enable,cs_n,ras_n,cas_n,we_n,data_mask_low,data_mask_high\n");
	$monitor("%g\t %h\t %b\t %b\t %b\t %b\t %h\t %h\t %h\t %b\t %h\t %h\t %h\t %b\t %b\t %b\t %b\t %b\t", $time, haddr, rd_enable, rd_ready, wr_enable, rst_n,data_r, data_input, data_output, busy, addr, bank_addr, data, clock_enable, cas_n, we_n, data_mask_low, data_mask_high);
	forever begin
	    @(posedge clk);
	    $fwrite(f,"%g,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b\n",
	    $time,data_output[15],data_output[14],data_output[13],data_output[12],data_output[11],data_output[10],data_output[9],data_output[8],data_output[7],data_output[6],data_output[5],data_output[4],data_output[3],data_output[2],data_output[1],data_output[0],rd_ready,addr[12],addr[11],addr[10],addr[9],addr[8],addr[7],addr[6],addr[5],addr[4],addr[3],addr[2],addr[1],addr[0],bank_addr[1],bank_addr[0],data[15],data[14],data[13],data[12],data[11],data[10],data[9],data[8],data[7],data[6],data[5],data[4],data[3],data[2],data[1],data[0],clock_enable,cs_n,ras_n,cas_n,we_n,data_mask_low,data_mask_high);
	end
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
    .rd_data(data_output), .rd_ready(rd_ready),
    .busy(busy), .rd_enable(rd_enable), .wr_enable(wr_enable), .rst_n(rst_n), .clk(clk),

    /* SDRAM SIDE */
    .addr(addr), .bank_addr(bank_addr), .data(data), .clock_enable(clock_enable), .cs_n(cs_n), .ras_n(ras_n), .cas_n(cas_n), .we_n(we_n), .data_mask_low(data_mask_low), .data_mask_high(data_mask_high)
);

endmodule
